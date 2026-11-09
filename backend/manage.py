"""Explicit administrative operations. No staff registration is exposed over HTTP."""

import argparse
import getpass
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import insert, select, update

from . import db
from .domain import event, now, recalculate, seed_rules, uid
from .security import hasher


def migrate():
    command.upgrade(Config(str(Path(__file__).parent.parent / "alembic.ini")), "head")
    with db.make_engine().begin() as con:
        seed_rules(con)


def create_user(email, name, role, password):
    from .schemas import Login

    body = Login(email=email, password=password)
    if len(password) < 12 or not 2 <= len(name.strip()) <= 80:
        raise ValueError("Nome inválido ou senha com menos de 12 caracteres.")
    user = dict(
        id=uid(),
        name=name.strip(),
        email=body.email,
        role=role,
        password_hash=hasher.hash(body.password),
        created_at=now(),
        privacy_version="2026-11-08",
    )
    with db.make_engine().begin() as con:
        con.execute(insert(db.users).values(**user))
        event(con, user["id"], "user", user["id"], "conta_criada_administrativamente", role)
    print("Conta criada. Perfil:", role)


def import_legacy(source, engine=None, data_dir=None):
    """Read-only source, unassigned dependents, idempotent import, original hashes checked."""
    source = Path(source).resolve()
    target = Path(data_dir or os.environ.get("IMUNIGUI_DATA_DIR", "data")).resolve()
    engine = engine or db.make_engine()
    if source == target:
        raise ValueError("Use um diretório de destino diferente para preservar o original.")
    source_db = source / "imuniguia.sqlite3"
    con_old = sqlite3.connect(source_db.as_uri() + "?mode=ro", uri=True)
    con_old.row_factory = sqlite3.Row
    people = [dict(r) for r in con_old.execute("SELECT * FROM dependents")]
    docs = [dict(r) for r in con_old.execute("SELECT * FROM documents")]
    events = [dict(r) for r in con_old.execute("SELECT * FROM audit_events")]
    con_old.close()
    for doc in docs:
        file = (source / "uploads" / doc["stored_name"]).resolve()
        if (
            file.parent != source / "uploads"
            or not file.is_file()
            or hashlib.sha256(file.read_bytes()).hexdigest() != doc["sha256"]
        ):
            raise ValueError("Arquivo ausente ou hash divergente; importação cancelada.")
    copied = []
    (target / "uploads").mkdir(parents=True, exist_ok=True)
    try:
        with engine.begin() as con:
            for p in people:
                if not con.execute(select(db.dependents.c.id).where(db.dependents.c.id == p["id"])).first():
                    con.execute(insert(db.dependents).values(**p, birth_date=None, owner_id=None))
            for doc in docs:
                existing = (
                    con.execute(select(db.documents).where(db.documents.c.id == doc["id"])).mappings().first()
                )
                if existing and existing["sha256"] != doc["sha256"]:
                    raise ValueError("ID existente com conteúdo diferente.")
                destination = target / "uploads" / doc["stored_name"]
                if (
                    destination.exists()
                    and hashlib.sha256(destination.read_bytes()).hexdigest() != doc["sha256"]
                ):
                    raise ValueError("Arquivo no destino diverge do original.")
                if not destination.exists():
                    shutil.copyfile(source / "uploads" / doc["stored_name"], destination)
                    copied.append(destination)
                if not existing:
                    con.execute(insert(db.documents).values(**doc))
                    con.execute(
                        insert(db.jobs).values(
                            id=uid(),
                            document_id=doc["id"],
                            status="queued",
                            attempts=0,
                            updated_at=now(),
                            error="",
                            raw_text="",
                        )
                    )
            for old in events:
                identifier = (
                    "legacy-" + hashlib.sha256(f"{old['document_id']}:{old['id']}".encode()).hexdigest()[:48]
                )
                if not con.execute(select(db.audit.c.id).where(db.audit.c.id == identifier)).first():
                    con.execute(
                        insert(db.audit).values(
                            id=identifier,
                            actor_id=None,
                            target_type="document",
                            target_id=old["document_id"],
                            event=old["event"],
                            details="LEGADO: autoria não autenticada. " + old["details"],
                            created_at=old["created_at"],
                        )
                    )
    except Exception:
        for file in copied:
            file.unlink(missing_ok=True)
        raise
    return {
        "dependents": len(people),
        "documents": len(docs),
        "audit_events": len(events),
        "verified_hashes": len(docs),
        "ownership": "Não atribuído; vincular administrativamente após verificação.",
    }


def main():
    parser = argparse.ArgumentParser(description="Administração ImuniGuia")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("migrate")
    sub.add_parser("sync-sources")
    profile = sub.add_parser("verify-reviewer")
    profile.add_argument("--email", required=True)
    profile.add_argument("--professional-id", required=True)
    profile.add_argument("--birth-city", required=True)
    profile.add_argument("--work-city", required=True)
    profile.add_argument("--verification-ref", required=True)

    sub.add_parser("privacy-requests")
    answer = sub.add_parser("answer-privacy")
    answer.add_argument("--id", required=True)
    answer.add_argument("--response", required=True)
    rule_import = sub.add_parser("activate-rules")
    rule_import.add_argument("file")
    user = sub.add_parser("create-user")
    user.add_argument("--email", required=True)
    user.add_argument("--name", required=True)
    user.add_argument("--role", choices=["familia", "ubs", "acs"], required=True)
    legacy = sub.add_parser("import-legacy")
    legacy.add_argument("directory")
    bind = sub.add_parser("bind-dependent")
    bind.add_argument("--dependent", required=True)
    bind.add_argument("--owner-email", required=True)
    bind.add_argument("--birth-date", required=True)
    args = parser.parse_args()
    if args.action == "migrate":
        migrate()
        print("Migrações aplicadas.")
    elif args.action == "sync-sources":
        from .sources import sync_catalog

        print(json.dumps(sync_catalog(os.environ.get("IMUNIGUI_DATA_DIR", "data")), ensure_ascii=False))
    elif args.action == "verify-reviewer":
        from .geography import location
        from .reviews import assign_waiting

        location(args.birth_city)
        location(args.work_city)
        if len(args.verification_ref.strip()) < 3 or len(args.professional_id.strip()) < 3:
            raise ValueError("Identificação profissional e referência da verificação obrigatórias.")
        with db.make_engine().begin() as con:
            user_id = con.execute(
                select(db.users.c.id).where(db.users.c.email == args.email.lower(), db.users.c.role == "ubs")
            ).scalar_one()
            if con.execute(
                select(db.reviewer_profiles.c.id).where(db.reviewer_profiles.c.user_id == user_id)
            ).first():
                raise ValueError("Perfil já verificado; alteração exige análise das atribuições existentes.")
            identifier = uid()
            con.execute(
                insert(db.reviewer_profiles).values(
                    id=identifier,
                    user_id=user_id,
                    professional_id=args.professional_id.strip(),
                    birth_city_code=args.birth_city,
                    work_city_code=args.work_city,
                    verified_at=now(),
                    verification_ref=args.verification_ref.strip(),
                )
            )
            event(
                con, None, "reviewer_profile", identifier, "verificacao_administrativa", args.verification_ref
            )
            assign_waiting(con)
        print("Perfil verificado e cadernetas aguardando equipe reavaliadas.")
    elif args.action == "privacy-requests":
        with db.make_engine().connect() as con:
            print(
                json.dumps(
                    [
                        dict(r)
                        for r in con.execute(
                            select(db.privacy_requests).where(db.privacy_requests.c.status == "recebida")
                        ).mappings()
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
            )
    elif args.action == "answer-privacy":
        if not 3 <= len(args.response.strip()) <= 2000:
            raise ValueError("Informe uma resposta entre 3 e 2000 caracteres.")
        with db.make_engine().begin() as con:
            row = (
                con.execute(select(db.privacy_requests).where(db.privacy_requests.c.id == args.id))
                .mappings()
                .one()
            )
            if row["status"] != "recebida":
                raise ValueError("Solicitação já respondida; histórico preservado.")
            con.execute(
                update(db.privacy_requests)
                .where(db.privacy_requests.c.id == args.id)
                .values(status="respondida", response=args.response.strip(), answered_at=now())
            )
            event(con, None, "privacy_request", args.id, "resposta_administrativa", args.response)
        print("Resposta registrada. A execução de correção ou eliminação deve ser verificada separadamente.")
    elif args.action == "activate-rules":
        from .schemas import RuleSet

        data = RuleSet.model_validate_json(Path(args.file).read_text(encoding="utf-8")).model_dump(
            mode="json"
        )
        with db.make_engine().begin() as con:
            if con.execute(select(db.rules.c.id).where(db.rules.c.version == data["version"])).first():
                raise ValueError("Versão já existe; publique uma nova versão sem sobrescrever o histórico.")
            con.execute(update(db.rules).values(active=False))
            identifier = uid()
            con.execute(insert(db.rules).values(id=identifier, active=True, created_at=now(), **data))
            event(con, None, "rule_set", identifier, "regras_ativadas_administrativamente", data["version"])
            for dependent_id in con.scalars(select(db.dependents.c.id)):
                recalculate(con, dependent_id)
        print("Nova versão de regras ativada e casos reavaliados.")
    elif args.action == "create-user":
        password = getpass.getpass("Senha (mínimo de 12 caracteres): ")
        if password != getpass.getpass("Repita a senha: "):
            raise ValueError("Senhas diferentes.")
        create_user(args.email, args.name, args.role, password)
    elif args.action == "import-legacy":
        print(json.dumps(import_legacy(args.directory), ensure_ascii=False, indent=2))
    elif args.action == "bind-dependent":
        from .schemas import Dependent

        with db.make_engine().begin() as con:
            p = (
                con.execute(select(db.dependents).where(db.dependents.c.id == args.dependent))
                .mappings()
                .one()
            )
            if p["owner_id"]:
                raise ValueError("Vínculo já atribuído; não será sobrescrito.")
            birth = Dependent(name=p["name"], birthDate=args.birth_date).birthDate.isoformat()
            owner = (
                con.execute(
                    select(db.users).where(
                        db.users.c.email == args.owner_email.lower(), db.users.c.role == "familia"
                    )
                )
                .mappings()
                .one()
            )
            con.execute(
                update(db.dependents)
                .where(db.dependents.c.id == args.dependent)
                .values(owner_id=owner["id"], birth_date=birth)
            )
            event(con, owner["id"], "dependent", args.dependent, "vinculo_legado_administrativo")
            recalculate(con, args.dependent, owner["id"])
        print("Vínculo atribuído e auditado.")


if __name__ == "__main__":
    main()
