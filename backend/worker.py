"""Durable SQL-backed OCR worker. Claims use compare-and-set; no in-memory job queue."""
import argparse
import hashlib
import os
import re
import subprocess
import tempfile
import time
import unicodedata
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytesseract
from PIL import Image
from pypdf import PdfReader
from sqlalchemy import insert, select, update

from . import db
from .access import one
from .domain import event, now, recalculate, uid

ALIASES = {'bcg': 'BCG', 'pentavalente': 'Pentavalente', 'penta': 'Pentavalente', 'poliomielite vip': 'Poliomielite VIP',
           'vip': 'Poliomielite VIP', 'hepatite b': 'Hepatite B', 'triplice viral': 'Tríplice viral', 'febre amarela': 'Febre amarela'}


def parse_candidates(text, confidence=0):
    """Only same-line vaccine + explicit dose + date; ambiguity stays for manual review."""
    candidates = []
    for line in text.splitlines():
        plain = ''.join(c for c in unicodedata.normalize('NFD', line.lower()) if not unicodedata.combining(c))
        vaccine = next((value for key, value in ALIASES.items() if re.search(r'\b' + re.escape(key) + r'\b', plain)), None)
        dose = re.search(r'\b([1-9])\s*(?:[aªº°.]\s*)?dose\b|\bdose\s*([1-9])\b', plain)
        day = re.search(r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b', plain)
        if vaccine and (dose or vaccine == 'BCG') and day:
            try:
                given = date(int(day[3]), int(day[2]), int(day[1]))
                if given > date.today() or given.year < 1900:
                    continue
            except ValueError:
                continue
            item = {'vaccine': vaccine, 'dose': int(dose[1] or dose[2]) if dose else 1, 'dose_date': given.isoformat(), 'confidence': confidence}
            if item not in candidates:
                candidates.append(item)
    return candidates


def image_ocr(path):
    with Image.open(path) as image:
        output = pytesseract.image_to_data(image, lang='por+eng', config='--psm 6', output_type=pytesseract.Output.DICT, timeout=90)
    lines, scores = {}, []
    for i, word in enumerate(output['text']):
        if not word.strip():
            continue
        key = (output['block_num'][i], output['par_num'][i], output['line_num'][i])
        lines.setdefault(key, []).append(word)
        score = float(output['conf'][i])
        if score >= 0:
            scores.append(score)
    return '\n'.join(' '.join(words) for words in lines.values()), round(sum(scores) / len(scores)) if scores else 0


def extract(path):
    if path.suffix.lower() != '.pdf':
        return image_ocr(path)
    pdf = PdfReader(path)
    text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
    if parse_candidates(text):
        return text[:20000], 0  # Embedded text has no OCR confidence score.
    with tempfile.TemporaryDirectory() as directory:
        prefix = str(Path(directory) / 'page')
        subprocess.run(['pdftoppm', '-scale-to', '2400', '-png', str(path), prefix], check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        parts = [image_ocr(page) for page in sorted(Path(directory).glob('page-*.png'))]
    return '\n'.join(p[0] for p in parts)[:20000], round(sum(p[1] for p in parts) / len(parts)) if parts else 0


def process_one(engine, data_dir, extractor=extract):
    stale = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat(timespec='microseconds')
    with engine.begin() as con:
        con.execute(update(db.jobs).where(db.jobs.c.status == 'processing', db.jobs.c.updated_at < stale).values(status='failed', error='Processamento interrompido; a UBS pode tentar novamente.', updated_at=now()))
        job = con.execute(select(db.jobs).where(db.jobs.c.status == 'queued').order_by(db.jobs.c.updated_at).limit(1)).mappings().first()
        if not job:
            return False
        claimed = con.execute(update(db.jobs).where(db.jobs.c.id == job['id'], db.jobs.c.status == 'queued').values(status='processing', attempts=job['attempts'] + 1, updated_at=now()))
        if not claimed.rowcount:
            return True
        document = one(con, db.documents, job['document_id'])
    try:
        root = Path(data_dir).resolve() / 'uploads'
        path = (root / document['stored_name']).resolve()
        if path.parent != root or hashlib.sha256(path.read_bytes()).hexdigest() != document['sha256']:
            raise ValueError('Integrity error')
        text, confidence = extractor(path)
        candidates = parse_candidates(text, confidence)
        with engine.begin() as con:
            for candidate in candidates:
                key = hashlib.sha256(f'{document["id"]}:{candidate["vaccine"]}:{candidate["dose"]}:{candidate["dose_date"]}'.encode()).hexdigest()
                if con.execute(select(db.vaccinations.c.id).where(db.vaccinations.c.source_key == key)).first():
                    continue
                identifier = uid()
                con.execute(insert(db.vaccinations).values(id=identifier, dependent_id=document['dependent_id'], document_id=document['id'], status='a_conferir', origin='ocr', source_key=key, reviewer_id=None, review_note='', created_at=now(), reviewed_at=None, **candidate))
                event(con, None, 'vaccination', identifier, 'ocr_candidato_criado')
            con.execute(update(db.jobs).where(db.jobs.c.id == job['id']).values(status='completed' if candidates else 'unreadable', raw_text=text[:20000], error='' if candidates else 'Leitura sem registros estruturados. A UBS pode transcrever a evidência manualmente.', updated_at=now()))
            event(con, None, 'document', document['id'], 'ocr_finalizado', f'{len(candidates)} candidato(s); conferência humana necessária.')
            recalculate(con, document['dependent_id'])
    except Exception:
        with engine.begin() as con:
            con.execute(update(db.jobs).where(db.jobs.c.id == job['id']).values(status='failed', error='Não foi possível processar a evidência. A UBS pode repetir ou transcrever manualmente.', updated_at=now()))
            event(con, None, 'document', document['id'], 'ocr_falhou')
    return True


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    engine = db.make_engine()
    data = Path(os.environ.get('IMUNIGUI_DATA_DIR', 'data'))
    last_refresh = 0
    while True:
        if time.monotonic() - last_refresh > 3600:
            with engine.begin() as con:
                for identifier in con.scalars(select(db.dependents.c.id)):
                    recalculate(con, identifier)
            last_refresh = time.monotonic()
        busy = process_one(engine, data)
        if args.once:
            break
        if not busy:
            time.sleep(3)


if __name__ == '__main__':
    run()
