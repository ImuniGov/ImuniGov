from fastapi import HTTPException
from sqlalchemy import select

from . import db
from . import security as sec


def one(con, table, identifier):
    row = con.execute(select(table).where(table.c.id == identifier)).mappings().first()
    if not row:
        raise HTTPException(404, "Item não encontrado.")
    return dict(row)


def person(con, identifier, user):
    sec.role(user, "familia", "ubs")
    item = one(con, db.dependents, identifier)
    if user["role"] == "familia" and item["owner_id"] != user["id"]:
        raise HTTPException(404, "Dependente não encontrado.")
    return item


def document(con, identifier, user):
    item = one(con, db.documents, identifier)
    return item, person(con, item["dependent_id"], user)


def public_document(row, dependent):
    names = {
        "dependent_id": "dependentId",
        "original_name": "fileName",
        "content_type": "contentType",
        "dose_date": "doseDate",
        "family_note": "familyNote",
        "review_note": "reviewNote",
        "created_at": "createdAt",
        "reviewed_at": "reviewedAt",
    }
    return {
        **{names.get(k, k): v for k, v in row.items() if k != "stored_name"},
        "dependent": dependent["name"],
        "fileUrl": f"/api/documents/{row['id']}/file",
    }
