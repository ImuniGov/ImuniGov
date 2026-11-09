"""Domain functions: no HTTP or trust in browser permissions."""

import calendar
import hashlib
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import insert, select, update

from . import db


def uid():
    return str(uuid.uuid4())


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def event(con, actor, kind, target, action, details=""):
    con.execute(
        insert(db.audit).values(
            id=uid(),
            actor_id=actor,
            target_type=kind,
            target_id=target,
            event=action,
            details=details[:1000],
            created_at=now(),
        )
    )


def notify(con, owner, key, message):
    key = hashlib.sha256(f"{owner}:{key}".encode()).hexdigest()
    if (
        owner
        and not con.execute(select(db.notifications.c.id).where(db.notifications.c.event_key == key)).first()
    ):
        con.execute(
            insert(db.notifications).values(
                id=uid(), user_id=owner, event_key=key, message=message, read=False, created_at=now()
            )
        )


def add_months(day, months):
    month = day.month - 1 + months
    year = day.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def evaluate(birth, records, rule_set, today=None):
    """Conservative routine rules: candidates never count as confirmed doses."""
    today = today or date.today()
    if not birth or not (rule_set["valid_from"] <= today.isoformat() <= rule_set["valid_until"]):
        return []
    birth = date.fromisoformat(birth)
    found = []
    accepted = {}
    confirmed = [r for r in records if r["status"] == "validado" and r["dose_date"]]
    for rule in sorted(rule_set["rules"], key=lambda r: (r["vaccine"], r["dose"])):
        if today < add_months(birth, rule["due_months"]) or today >= add_months(birth, rule["max_months"]):
            continue
        matching = [r for r in confirmed if r["vaccine"] == rule["vaccine"] and r["dose"] == rule["dose"]]
        reason = "Nenhum registro confirmado para esta dose no histórico disponível."
        satisfied = False
        for record in matching:
            given = date.fromisoformat(record["dose_date"])
            if (
                given < add_months(birth, rule.get("min_months", rule["due_months"]))
                or (given - birth).days < rule.get("min_age_days", 0)
                or given > today
            ):
                reason = "Data do registro requer conferência da UBS quanto à idade mínima."
                continue
            previous = accepted.get((rule["vaccine"], rule["dose"] - 1))
            first = accepted.get((rule["vaccine"], 1))
            if (rule.get("min_interval_days", 0) or rule.get("min_interval_months", 0)) and (
                not previous
                or (given - previous).days < rule.get("min_interval_days", 0)
                or given < add_months(previous, rule.get("min_interval_months", 0))
            ):
                reason = "Sequência ou intervalo entre doses requer conferência da UBS."
                continue
            if rule.get("min_from_first_months") and (
                not first or given < add_months(first, rule["min_from_first_months"])
            ):
                reason = "Intervalo desde a primeira dose requer conferência da UBS."
                continue
            satisfied = True
            old_date = accepted.get((rule["vaccine"], rule["dose"]))
            accepted[(rule["vaccine"], rule["dose"])] = min(old_date, given) if old_date else given
        if not satisfied:
            candidate = any(
                r["vaccine"] == rule["vaccine"] and r["dose"] == rule["dose"] and r["status"] == "a_conferir"
                for r in records
            )
            found.append({**rule, "reason": reason + (" Existe informação a conferir." if candidate else "")})
    return found


def recalculate(con, dependent_id, actor=None, today=None):
    dependent = con.execute(select(db.dependents).where(db.dependents.c.id == dependent_id)).mappings().one()
    active = con.execute(select(db.rules).where(db.rules.c.active.is_(True))).mappings().first()
    if not active:
        return []
    today = today or date.today()
    if not (active["valid_from"] <= today.isoformat() <= active["valid_until"]):
        return []  # Never resolve old findings merely because a ruleset expired.
    records = (
        con.execute(select(db.vaccinations).where(db.vaccinations.c.dependent_id == dependent_id))
        .mappings()
        .all()
    )
    found = evaluate(dependent["birth_date"], records, active, today)
    expected = {r["id"] for r in found}
    old = con.execute(select(db.pendings).where(db.pendings.c.dependent_id == dependent_id)).mappings().all()
    for item in old:
        if item["status"] == "aberta" and (
            item["rule_set_id"] != active["id"] or item["rule_id"] not in expected
        ):
            con.execute(
                update(db.pendings)
                .where(db.pendings.c.id == item["id"])
                .values(status="resolvida", updated_at=now())
            )
            event(con, actor, "pending", item["id"], "pendencia_resolvida")
            notify(
                con,
                dependent["owner_id"],
                f"resolved:{item['id']}:{item['updated_at']}",
                "Uma possível pendência foi reavaliada. Consulte o acompanhamento.",
            )
    for rule in found:
        existing = next(
            (p for p in old if p["rule_id"] == rule["id"] and p["rule_set_id"] == active["id"]), None
        )
        if existing:
            if existing["status"] == "aberta" and existing["reason"] == rule["reason"]:
                continue
            con.execute(
                update(db.pendings)
                .where(db.pendings.c.id == existing["id"])
                .values(status="aberta", reason=rule["reason"], updated_at=now())
            )
            target = existing["id"]
        else:
            target = uid()
            con.execute(
                insert(db.pendings).values(
                    id=target,
                    dependent_id=dependent_id,
                    rule_set_id=active["id"],
                    rule_id=rule["id"],
                    vaccine=rule["vaccine"],
                    dose=rule["dose"],
                    reason=rule["reason"],
                    status="aberta",
                    updated_at=now(),
                )
            )
        event(con, actor, "pending", target, "pendencia_identificada")
        notify(
            con,
            dependent["owner_id"],
            f"pending:{target}:{existing['updated_at'] if existing else 'new'}",
            f"Possível pendência: {rule['vaccine']}, dose {rule['dose']}. Consulte a UBS.",
        )
    for upcoming in schedule(dependent["birth_date"], records, active, today):
        if 0 <= upcoming["daysUntil"] <= 30:
            notify(
                con,
                dependent["owner_id"],
                f"upcoming:{dependent_id}:{active['id']}:{upcoming['ruleId']}:{upcoming['dueDate']}",
                f"Data recomendada se aproxima: {upcoming['vaccine']}, dose {upcoming['dose']}, em {upcoming['dueDate']}. Confira o acompanhamento da família.",
            )
    return found


def schedule(birth, records, rule_set, today=None):
    today = today or date.today()
    if not birth or not (rule_set["valid_from"] <= today.isoformat() <= rule_set["valid_until"]):
        return []
    born = date.fromisoformat(birth)
    items = []
    missing = {r["id"] for r in evaluate(birth, records, rule_set, today)}
    for rule in rule_set["rules"]:
        due = add_months(born, rule["due_months"])
        if today >= add_months(born, rule["max_months"]):
            continue
        confirmed = any(
            r["status"] == "validado"
            and r["vaccine"] == rule["vaccine"]
            and r["dose"] == rule["dose"]
            and r["dose_date"]
            for r in records
        )
        # A future dose already recorded must not suppress an alert unless valid for the rules.
        if confirmed and (due > today or rule["id"] not in missing):
            future_check = evaluate(birth, records, rule_set, max(today, due))
            if rule["id"] not in {r["id"] for r in future_check}:
                continue
        days = (due - today).days
        items.append(
            {
                "ruleId": rule["id"],
                "vaccine": rule["vaccine"],
                "dose": rule["dose"],
                "dueDate": due.isoformat(),
                "daysUntil": days,
                "status": "atrasada" if days < 0 else "proxima" if days <= 30 else "prevista",
                "hasCandidate": any(
                    r["status"] == "a_conferir"
                    and r["vaccine"] == rule["vaccine"]
                    and r["dose"] == rule["dose"]
                    for r in records
                ),
                "ruleVersion": rule_set["version"],
                "source": rule_set["source"],
            }
        )
    return sorted(items, key=lambda item: (item["dueDate"], item["vaccine"]))


def seed_rules(con):
    path = Path(__file__).parent / "rules" / "routine-2026.json"
    if not path.exists():
        return
    from .schemas import RuleSet

    data = RuleSet.model_validate_json(path.read_text(encoding="utf-8")).model_dump(mode="json")
    if not con.execute(select(db.rules.c.id).where(db.rules.c.version == data["version"])).first():
        con.execute(insert(db.rules).values(id=uid(), active=True, created_at=now(), **data))
