"""Authorization for this voluntary digital workflow, distinct from retention duties."""

import hashlib
import json
from pathlib import Path

from sqlalchemy import and_, select

from . import db

POLICY_PATH = Path(__file__).parent / "legal" / "privacy-2026-11-08-v3.json"


def policy():
    raw = POLICY_PATH.read_bytes()
    return {**json.loads(raw), "hash": hashlib.sha256(raw).hexdigest()}


def permitted_owner(owner):
    current = policy()
    return and_(
        select(db.acceptances.c.id)
        .where(
            db.acceptances.c.user_id == owner,
            db.acceptances.c.version == current["version"],
            db.acceptances.c.policy_hash == current["hash"],
        )
        .exists(),
        ~select(db.consent_controls.c.id)
        .where(db.consent_controls.c.user_id == owner, db.consent_controls.c.withdrawn.is_(True))
        .exists(),
    )


def allowed(con, owner, lock=False):
    if not owner:
        return False
    query = select(db.users.c.id).where(db.users.c.id == owner)
    if lock:
        query = query.with_for_update()
    if not con.execute(query).first():
        return False
    return bool(con.scalar(select(permitted_owner(owner))))


def state(con, owner):
    control = (
        con.execute(select(db.consent_controls).where(db.consent_controls.c.user_id == owner))
        .mappings()
        .first()
    )
    return {
        "current": allowed(con, owner),
        "withdrawn": bool(control and control["withdrawn"]),
        "version": policy()["version"],
    }


def authorization_token(con, owner):
    current = policy()
    return con.scalar(
        select(db.acceptances.c.id)
        .where(
            db.acceptances.c.user_id == owner,
            db.acceptances.c.version == current["version"],
            db.acceptances.c.policy_hash == current["hash"],
        )
        .order_by(db.acceptances.c.accepted_at.desc(), db.acceptances.c.id.desc())
        .limit(1)
    )
