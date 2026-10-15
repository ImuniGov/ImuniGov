"""Servidor local do módulo de envio e revisão do ImuniGuia.

Uso: python server.py
Os dados ficam em ./data (SQLite e arquivos privados, fora da pasta pública).
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("IMUNIGUI_DATA_DIR", ROOT / "data")).resolve()
FILES_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "imuniguia.sqlite3"
MAX_UPLOAD = 10 * 1024 * 1024
MAX_REQUEST = MAX_UPLOAD + 128 * 1024
HOST = os.environ.get("IMUNIGUI_HOST", "127.0.0.1")
PORT = int(os.environ.get("IMUNIGUI_PORT", "4173"))

MIME_SIGNATURES = {
    "image/jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "image/png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "image/webp": lambda b: len(b) >= 12 and b[:4] == b"RIFF" and b[8:12] == b"WEBP",
    "application/pdf": lambda b: b[:1024].lstrip().startswith(b"%PDF-"),
}


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect():
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def initialize():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS dependents (
            id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            dependent_id TEXT NOT NULL REFERENCES dependents(id),
            original_name TEXT NOT NULL,
            stored_name TEXT NOT NULL UNIQUE,
            content_type TEXT NOT NULL,
            size INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            vaccine TEXT NOT NULL,
            dose_date TEXT,
            family_note TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'pendente' CHECK(status IN ('pendente','aprovado','rejeitado')),
            review_note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewer TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS documents_status_created ON documents(status, created_at DESC);
        CREATE INDEX IF NOT EXISTS documents_dependent ON documents(dependent_id, created_at DESC);
        CREATE TABLE IF NOT EXISTS audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            document_id TEXT NOT NULL REFERENCES documents(id),
            event TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        """)


def public_document(row):
    return {
        "id": row["id"], "dependentId": row["dependent_id"],
        "dependent": row["dependent_name"], "fileName": row["original_name"],
        "contentType": row["content_type"], "size": row["size"], "sha256": row["sha256"],
        "vaccine": row["vaccine"], "doseDate": row["dose_date"],
        "familyNote": row["family_note"], "status": row["status"],
        "reviewNote": row["review_note"], "createdAt": row["created_at"],
        "reviewedAt": row["reviewed_at"], "reviewer": row["reviewer"],
        "fileUrl": f"/api/documents/{row['id']}/file",
    }


class ApiError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class Handler(BaseHTTPRequestHandler):
    server_version = "ImuniGuia/1.0"

    def log_message(self, fmt, *args):
        # Avoid writing submitted names, filenames, or request bodies to terminal logs.
        super().log_message(fmt, *args)

    def headers_common(self, content_type="application/json; charset=utf-8", allow_frame=False):
        self.send_header("Content-Type", content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "SAMEORIGIN" if allow_frame else "DENY")
        self.send_header("Cache-Control", "no-store")
        if allow_frame:
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'self'")
        elif self.path.startswith("/api/"):
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        else:
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")

    def json_response(self, status, payload):
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.headers_common()
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def empty_response(self, status=204):
        self.send_response(status)
        self.headers_common()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def body(self, limit=MAX_REQUEST):
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ApiError(400, "Tamanho da requisição inválido.")
        if size <= 0:
            raise ApiError(400, "A requisição não contém dados.")
        if size > limit:
            raise ApiError(413, "O arquivo excede o limite de 10 MB.")
        return self.rfile.read(size)

    def json_body(self):
        try:
            return json.loads(self.body(64 * 1024).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(400, "Envie um JSON válido.")

    def multipart_body(self):
        ctype = self.headers.get("Content-Type", "")
        if not ctype.lower().startswith("multipart/form-data;"):
            raise ApiError(415, "O envio deve usar multipart/form-data.")
        message = BytesParser(policy=policy.default).parsebytes(
            b"Content-Type: " + ctype.encode("ascii", "ignore") + b"\r\nMIME-Version: 1.0\r\n\r\n" + self.body()
        )
        if not message.is_multipart():
            raise ApiError(400, "Não foi possível ler os campos do envio.")
        fields, upload = {}, None
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            value = part.get_payload(decode=True) or b""
            filename = part.get_filename()
            if filename is not None:
                if name == "file":
                    upload = (filename, part.get_content_type().lower(), value)
            else:
                charset = part.get_content_charset() or "utf-8"
                fields[name] = value.decode(charset, "replace").strip()
        return fields, upload

    def record_event(self, con, document_id, event, details=""):
        con.execute("INSERT INTO audit_events(document_id,event,details,created_at) VALUES(?,?,?,?)", (document_id, event, details[:300], now()))

    def get_document(self, con, document_id):
        row = con.execute("""SELECT d.*, p.name dependent_name FROM documents d
            JOIN dependents p ON p.id=d.dependent_id WHERE d.id=?""", (document_id,)).fetchone()
        if not row:
            raise ApiError(404, "Documento não encontrado.")
        return row

    def do_GET(self):
        try:
            path = unquote(urlparse(self.path).path)
            if path in ("/", "/index.html"):
                return self.static("index.html", "text/html; charset=utf-8")
            if path in ("/styles.css", "/app.js"):
                file = path[1:]
                return self.static(file, "text/css; charset=utf-8" if file.endswith(".css") else "text/javascript; charset=utf-8")
            if path == "/api/health":
                return self.json_response(200, {"ok": True, "service": "ImuniGuia upload-and-review"})
            if path == "/api/dependents":
                with connect() as con:
                    rows = con.execute("""SELECT p.id,p.name,p.created_at,COUNT(d.id) document_count
                        FROM dependents p LEFT JOIN documents d ON d.dependent_id=p.id
                        GROUP BY p.id ORDER BY p.name COLLATE NOCASE""").fetchall()
                return self.json_response(200, {"items": [dict(r) for r in rows]})
            if path == "/api/documents":
                status = self.query_value("status")
                if status and status not in ("pendente", "aprovado", "rejeitado"):
                    raise ApiError(400, "Filtro de status inválido.")
                query = """SELECT d.*,p.name dependent_name FROM documents d
                    JOIN dependents p ON p.id=d.dependent_id"""
                args = []
                if status:
                    query += " WHERE d.status=?"
                    args.append(status)
                query += " ORDER BY d.created_at DESC"
                with connect() as con:
                    rows = con.execute(query, args).fetchall()
                return self.json_response(200, {"items": [public_document(row) for row in rows]})
            match = re.fullmatch(r"/api/documents/([0-9a-f-]{36})", path)
            if match:
                with connect() as con:
                    row = self.get_document(con, match.group(1))
                return self.json_response(200, {"item": public_document(row)})
            match = re.fullmatch(r"/api/documents/([0-9a-f-]{36})/file", path)
            if match:
                with connect() as con:
                    row = self.get_document(con, match.group(1))
                stored = (FILES_DIR / row["stored_name"]).resolve()
                if stored.parent != FILES_DIR or not stored.is_file():
                    raise ApiError(404, "Arquivo não encontrado.")
                data = stored.read_bytes()
                safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", row["original_name"])[:120] or "documento"
                self.send_response(200)
                self.headers_common(row["content_type"], allow_frame=True)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Content-Disposition", f'inline; filename="{safe_name}"; filename*=UTF-8\'\'{quote(row["original_name"])}')
                self.end_headers()
                self.wfile.write(data)
                return
            if path == "/api/audit":
                doc_id = self.query_value("documentId")
                if not doc_id:
                    raise ApiError(400, "Informe documentId para consultar o histórico.")
                with connect() as con:
                    self.get_document(con, doc_id)
                    rows = con.execute("SELECT event,details,created_at FROM audit_events WHERE document_id=? ORDER BY id", (doc_id,)).fetchall()
                return self.json_response(200, {"items": [dict(r) for r in rows]})
            return self.json_response(404, {"error": "Rota não encontrada."})
        except ApiError as error:
            return self.json_response(error.status, {"error": error.message})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self.log_error("GET request failed")
            return self.json_response(500, {"error": "Erro interno ao consultar os dados."})

    def query_value(self, key):
        from urllib.parse import parse_qs
        return parse_qs(urlparse(self.path).query).get(key, [None])[0]

    def do_POST(self):
        try:
            path = unquote(urlparse(self.path).path)
            if path.startswith("/api/") and not self.same_origin():
                raise ApiError(403, "Origem da requisição não permitida.")
            if path == "/api/dependents":
                body = self.json_body()
                name = self.clean_text(body.get("name"), 80, "Informe o nome do dependente.")
                dependent_id = str(uuid.uuid4())
                with connect() as con:
                    con.execute("INSERT INTO dependents(id,name,created_at) VALUES(?,?,?)", (dependent_id, name, now()))
                return self.json_response(201, {"item": {"id": dependent_id, "name": name, "created_at": now(), "document_count": 0}})
            if path == "/api/documents":
                return self.create_document()
            match = re.fullmatch(r"/api/documents/([0-9a-f-]{36})/decision", path)
            if match:
                return self.decide(match.group(1))
            return self.json_response(404, {"error": "Rota não encontrada."})
        except ApiError as error:
            return self.json_response(error.status, {"error": error.message})
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception:
            self.log_error("POST request failed")
            return self.json_response(500, {"error": "Erro interno ao salvar os dados."})

    def same_origin(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        host = self.headers.get("Host", "").lower()
        parsed = urlparse(origin)
        return parsed.netloc.lower() == host and parsed.scheme in ("http", "https")

    @staticmethod
    def clean_text(value, max_len, missing_message, required=True):
        value = value.strip() if isinstance(value, str) else ""
        value = " ".join(value.split())
        if required and not value:
            raise ApiError(400, missing_message)
        if len(value) > max_len:
            raise ApiError(400, f"O texto excede o limite de {max_len} caracteres.")
        if any(ord(ch) < 32 for ch in value):
            raise ApiError(400, "O texto contém caracteres inválidos.")
        return value

    def create_document(self):
        fields, upload = self.multipart_body()
        dependent_id = fields.get("dependentId", "")
        vaccine = self.clean_text(fields.get("vaccine"), 80, "Informe o tipo de registro.")
        family_note = self.clean_text(fields.get("note", ""), 500, "", required=False)
        dose_date = fields.get("doseDate", "") or None
        if dose_date:
            try:
                datetime.strptime(dose_date, "%Y-%m-%d")
            except ValueError:
                raise ApiError(400, "Data do registro inválida.")
        if not upload:
            raise ApiError(400, "Selecione um arquivo para enviar.")
        original_name, content_type, blob = upload
        if not original_name or not blob:
            raise ApiError(400, "O arquivo enviado está vazio.")
        if len(blob) > MAX_UPLOAD:
            raise ApiError(413, "O arquivo excede o limite de 10 MB.")
        valid_signature = MIME_SIGNATURES.get(content_type)
        if not valid_signature or not valid_signature(blob[:1024]):
            raise ApiError(415, "O formato real do arquivo não corresponde a JPG, PNG, WEBP ou PDF.")
        suffix = {"image/jpeg":".jpg","image/png":".png","image/webp":".webp","application/pdf":".pdf"}[content_type]
        original_name = Path(original_name.replace("\\", "/")).name
        original_name = "".join(ch for ch in original_name if ord(ch) >= 32)[:180] or f"caderneta{suffix}"
        document_id, stored_name = str(uuid.uuid4()), f"{uuid.uuid4().hex}{suffix}"
        checksum = hashlib.sha256(blob).hexdigest()
        temp_path, final_path = FILES_DIR / f".{stored_name}.tmp", FILES_DIR / stored_name
        try:
            with temp_path.open("xb") as stream:
                stream.write(blob)
            os.replace(temp_path, final_path)
            with connect() as con:
                if not con.execute("SELECT 1 FROM dependents WHERE id=?", (dependent_id,)).fetchone():
                    raise ApiError(404, "Dependente não encontrado. Cadastre o dependente antes do envio.")
                con.execute("""INSERT INTO documents(id,dependent_id,original_name,stored_name,content_type,size,sha256,vaccine,dose_date,family_note,created_at)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?)""", (document_id, dependent_id, original_name, stored_name, content_type, len(blob), checksum, vaccine, dose_date, family_note, now()))
                self.record_event(con, document_id, "arquivo_enviado", "Documento recebido e aguardando análise.")
                row = self.get_document(con, document_id)
            return self.json_response(201, {"item": public_document(row)})
        except Exception:
            final_path.unlink(missing_ok=True)
            raise
        finally:
            temp_path.unlink(missing_ok=True)

    def decide(self, document_id):
        body = self.json_body()
        decision = body.get("decision")
        if decision not in ("aprovado", "rejeitado"):
            raise ApiError(400, "A decisão deve ser aprovado ou rejeitado.")
        reviewer = self.clean_text(body.get("reviewer"), 80, "Informe o nome de quem está revisando.")
        note = self.clean_text(body.get("note", ""), 300, "Informe o motivo da devolução.", required=decision == "rejeitado")
        if decision == "aprovado" and not note:
            note = "Documento conferido pela equipe."
        with connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = self.get_document(con, document_id)
            if row["status"] != "pendente":
                raise ApiError(409, "Este documento já recebeu uma decisão.")
            timestamp = now()
            con.execute("UPDATE documents SET status=?,review_note=?,reviewed_at=?,reviewer=? WHERE id=?", (decision, note, timestamp, reviewer, document_id))
            self.record_event(con, document_id, decision, f"{reviewer}: {note}")
            updated = self.get_document(con, document_id)
        return self.json_response(200, {"item": public_document(updated)})

    def static(self, name, content_type):
        file = (ROOT / name).resolve()
        if file.parent != ROOT or not file.is_file():
            return self.json_response(404, {"error": "Arquivo não encontrado."})
        data = file.read_bytes()
        self.send_response(200)
        self.headers_common(content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_DELETE(self):
        try:
            path = unquote(urlparse(self.path).path)
            if path.startswith("/api/") and not self.same_origin():
                raise ApiError(403, "Origem da requisição não permitida.")
            match = re.fullmatch(r"/api/dependents/([0-9a-f-]{36})", path)
            if not match:
                return self.json_response(404, {"error": "Rota não encontrada."})
            dependent_id = match.group(1)
            with connect() as con:
                con.execute("BEGIN IMMEDIATE")
                if con.execute("SELECT 1 FROM documents WHERE dependent_id=?", (dependent_id,)).fetchone():
                    raise ApiError(409, "Não é possível remover um dependente que possui documentos associados.")
                cur = con.execute("DELETE FROM dependents WHERE id=?", (dependent_id,))
                if not cur.rowcount:
                    raise ApiError(404, "Dependente não encontrado.")
            return self.empty_response()
        except ApiError as error:
            return self.json_response(error.status, {"error": error.message})
        except Exception:
            self.log_error("DELETE request failed")
            return self.json_response(500, {"error": "Erro interno ao remover o dependente."})


def main():
    initialize()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"ImuniGuia disponível em http://{HOST}:{PORT}")
    print(f"Banco e arquivos privados: {DATA_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando ImuniGuia…")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
