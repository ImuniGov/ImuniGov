"""Portable database+immutable-files backup; restore only to a fresh migrated database."""

import argparse
import hashlib
import io
import json
import os
import tarfile
from pathlib import Path

from sqlalchemy import delete, func, insert, inspect, select, text

from . import db

EXCLUDED = {"sessions", "auth_attempts", "push_subscriptions"}
SCHEMA_VERSION = "012"
COMPATIBLE_SCHEMAS = {"001", SCHEMA_VERSION}
INITIAL_GATE = [{"id": "roster", "revision": 1}]


def _check_revision(con):
    if "alembic_version" in inspect(con).get_table_names():
        revisions = list(con.scalars(text("SELECT version_num FROM alembic_version")))
        if revisions != [SCHEMA_VERSION]:
            raise ValueError("Versão de migração do banco incompatível.")


def backup(engine, data_dir, destination):
    data_dir, destination = Path(data_dir).resolve(), Path(destination).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    rows = {}
    with engine.connect() as con:
        if engine.dialect.name == "postgresql":
            con = con.execution_options(isolation_level="REPEATABLE READ")
        with con.begin():
            _check_revision(con)
            for table in db.metadata.sorted_tables:
                if table.name not in EXCLUDED:
                    rows[table.name] = [dict(r) for r in con.execute(select(table)).mappings()]
            with tarfile.open(destination, "x:gz") as archive:
                blob = json.dumps({"schema": SCHEMA_VERSION, "tables": rows}, ensure_ascii=False).encode()
                info = tarfile.TarInfo("database.json")
                info.size = len(blob)
                archive.addfile(info, io.BytesIO(blob))
                for doc in rows["documents"]:
                    path = (data_dir / "uploads" / doc["stored_name"]).resolve()
                    if (
                        path.parent != data_dir / "uploads"
                        or not path.is_file()
                        or hashlib.sha256(path.read_bytes()).hexdigest() != doc["sha256"]
                    ):
                        raise ValueError("Hash divergente: backup não pode ser considerado válido.")
                    archive.add(path, arcname="uploads/" + doc["stored_name"])
    return {name: len(items) for name, items in rows.items()}


def restore(engine, data_dir, source):
    data_dir = Path(data_dir).resolve()
    copied = []
    try:
        with tarfile.open(source, "r:gz") as archive, engine.begin() as con:
            _check_revision(con)
            handle = archive.extractfile("database.json")
            manifest = json.load(handle)
            tables = manifest.get("tables")
            if (
                manifest.get("schema") not in COMPATIBLE_SCHEMAS
                or not isinstance(tables, dict)
                or set(tables) != set(db.metadata.tables) - EXCLUDED
            ):
                raise ValueError("Versão ou tabelas incompatíveis.")
            for table in db.metadata.sorted_tables:
                if table.name in EXCLUDED:
                    continue
                valid_cols = {c.name for c in table.columns}
                for row in tables.get(table.name, []):
                    if not isinstance(row, dict) or not set(row).issubset(valid_cols):
                        raise ValueError("Versão ou tabelas incompatíveis.")
            for table in db.metadata.sorted_tables:
                if table.name == "review_gate":
                    gate = [dict(r) for r in con.execute(select(db.review_gate)).mappings()]
                    if gate not in ([], INITIAL_GATE):
                        raise ValueError(
                            "Restauração exige banco novo e vazio; nenhum dado será sobrescrito."
                        )
                elif con.scalar(select(func.count()).select_from(table)):
                    raise ValueError("Restauração exige banco novo e vazio; nenhum dado será sobrescrito.")
            for doc in tables["documents"]:
                path = (data_dir / "uploads" / doc["stored_name"]).resolve()
                if path.parent != data_dir / "uploads" or path.exists():
                    raise ValueError("Caminho inválido ou arquivo já existente no destino.")
                try:
                    member = archive.getmember("uploads/" + doc["stored_name"])
                except KeyError as exc:
                    raise ValueError("Arquivo inválido no backup.") from exc
                if not member.isfile() or member.size > 10 * 1024 * 1024:
                    raise ValueError("Arquivo inválido no backup.")
                blob = archive.extractfile(member).read()
                if hashlib.sha256(blob).hexdigest() != doc["sha256"]:
                    raise ValueError("Hash divergente no backup.")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(blob)
                copied.append(path)
            con.execute(delete(db.review_gate))
            for table in db.metadata.sorted_tables:
                rows = tables.get(table.name, [])
                if table.name == "review_gate" and not rows:
                    rows = INITIAL_GATE
                if rows:
                    con.execute(insert(table), rows)
    except Exception:
        for path in copied:
            path.unlink(missing_ok=True)
        raise
    return {k: len(v) for k, v in manifest["tables"].items()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["create", "restore"])
    parser.add_argument("archive")
    args = parser.parse_args()
    engine = db.make_engine()
    directory = os.environ.get("IMUNIGUI_DATA_DIR", "data")
    result = (
        backup(engine, directory, args.archive)
        if args.action == "create"
        else restore(engine, directory, args.archive)
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
