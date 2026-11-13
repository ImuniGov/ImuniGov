from fastapi import HTTPException
from sqlalchemy import select

from . import db
from . import security as sec
from .consents import allowed
from .reviews import require_assignment, summary


def one(con, table, identifier):
    row = con.execute(select(table).where(table.c.id == identifier)).mappings().first()
    if not row:
        raise HTTPException(404, "Item não encontrado.")
    return dict(row)


def person(con, identifier, user):
    sec.role(user, "familia", "ubs")
    item = one(con, db.dependents, identifier)
    if user["role"] == "familia" and user.get("_write") and not allowed(con, user["id"], lock=True):
        raise HTTPException(403, "Acompanhamento digital pausado. Confira sua autorização.")
    if user["role"] == "familia" and item["owner_id"] != user["id"]:
        raise HTTPException(404, "Dependente não encontrado.")
    if user["role"] == "ubs" and not allowed(con, item["owner_id"], lock=True):
        raise HTTPException(403, "O acompanhamento digital desta família está pausado.")
    if (
        user["role"] == "ubs"
        and not con.execute(
            select(db.review_assignments.c.id)
            .join(db.documents, db.documents.c.id == db.review_assignments.c.document_id)
            .where(
                db.documents.c.dependent_id == identifier,
                db.review_assignments.c.reviewer_id == user["id"],
                db.review_assignments.c.status == "ativa",
            )
            .limit(1)
        ).first()
    ):
        raise HTTPException(403, "O dependente não está atribuído à sua equipe de revisão.")
    return item


def document(con, identifier, user):
    sec.role(user, "familia", "ubs")
    item = one(con, db.documents, identifier)
    require_assignment(con, identifier, user)
    return item, person(con, item["dependent_id"], user)


def public_document(row, dependent, con, user):
    names = {
        "dependent_id": "dependentId",
        "original_name": "fileName",
        "content_type": "contentType",
        "dose_date": "doseDate",
        "family_note": "familyNote",
        "review_note": "reviewNote",
        "review_guidance": "reviewGuidance",
        "review_hold": "reviewHold",
        "created_at": "createdAt",
        "reviewed_at": "reviewedAt",
    }
    return {
        **{names.get(k, k): v for k, v in row.items() if k != "stored_name"},
        "dependent": dependent["name"],
        "fileUrl": f"/api/documents/{row['id']}/file",
        "review": summary(con, row["id"], "document", row["id"], user, terminal=row["status"] != "pendente"),
    }
