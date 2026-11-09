import hashlib
import sqlite3

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from backend import db
from backend.backup import backup, restore
from backend.manage import import_legacy


def test_migrate_legacy_backup_restore(tmp_path, monkeypatch):
    target = tmp_path / 'target'
    target.mkdir()
    url = 'sqlite:///' + str(target / 'app.sqlite3')
    monkeypatch.setenv('DATABASE_URL', url)
    command.upgrade(Config('alembic.ini'), 'head')
    command.upgrade(Config('alembic.ini'), 'head')
    engine = db.make_engine(url)
    legacy = tmp_path / 'legacy'
    (legacy / 'uploads').mkdir(parents=True)
    original = b'synthetic original bytes'
    (legacy / 'uploads' / 'legacy.png').write_bytes(original)
    con = sqlite3.connect(legacy / 'imuniguia.sqlite3')
    con.executescript('''
      CREATE TABLE dependents(id TEXT PRIMARY KEY, name TEXT, created_at TEXT);
      CREATE TABLE documents(id TEXT PRIMARY KEY, dependent_id TEXT, original_name TEXT, stored_name TEXT, content_type TEXT, size INTEGER, sha256 TEXT, vaccine TEXT, dose_date TEXT, family_note TEXT, status TEXT, review_note TEXT, created_at TEXT, reviewed_at TEXT, reviewer TEXT);
      CREATE TABLE audit_events(id INTEGER PRIMARY KEY, document_id TEXT, event TEXT, details TEXT, created_at TEXT);
      INSERT INTO dependents VALUES('person','Sintético','2026-01-01');
      INSERT INTO audit_events VALUES(1,'doc','arquivo_enviado','Entrega antiga','2026-01-01');
    ''')
    con.execute('INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', ('doc', 'person', 'original.png', 'legacy.png', 'image/png', len(original), hashlib.sha256(original).hexdigest(), 'BCG', '2026-01-01', '', 'pendente', '', '2026-01-01', None, ''))
    con.commit()
    con.close()
    first = import_legacy(legacy, engine, target)
    assert first['verified_hashes'] == 1
    assert import_legacy(legacy, engine, target) == first
    with engine.connect() as con:
        person = con.execute(select(db.dependents)).mappings().one()
        assert person['owner_id'] is None
        assert con.scalar(select(func.count()).select_from(db.documents)) == 1
        assert con.scalar(select(func.count()).select_from(db.audit)) == 1
    archive = tmp_path / 'backup.tgz'
    before = backup(engine, target, archive)
    restored_dir = tmp_path / 'restored'
    restored_dir.mkdir()
    restored_engine = db.make_engine('sqlite:///' + str(restored_dir / 'app.sqlite3'))
    db.metadata.create_all(restored_engine)
    assert restore(restored_engine, restored_dir, archive) == before
    assert (restored_dir / 'uploads' / 'legacy.png').read_bytes() == original
    with pytest.raises(ValueError, match='novo e vazio'):
        restore(restored_engine, restored_dir, archive)
    (legacy / 'uploads' / 'legacy.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='hash divergente'):
        import_legacy(legacy, engine, target)
    engine.dispose()
    restored_engine.dispose()
