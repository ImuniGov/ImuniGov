import hashlib
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def catalog():
    return json.loads((Path(__file__).parent / "data" / "geography.json").read_text(encoding="utf-8"))


def location(code):
    try:
        return {"code": str(code), **catalog()["municipalities"][str(code)]}
    except KeyError as exc:
        raise ValueError("Município não consta do catálogo oficial do IBGE.") from exc


def profile_snapshot(profile):
    birth, work = location(profile["birth_city_code"]), location(profile["work_city_code"])
    values = {
        "profileId": profile["id"],
        "professionalId": profile["professional_id"],
        "birth": birth,
        "work": work,
        "verifiedAt": profile["verified_at"],
        "catalogVersion": catalog()["version"],
    }
    values["fingerprint"] = hashlib.sha256(
        json.dumps(values, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    return values


def compatible(a, b):
    """Every birth/work combination across two people must differ in city, UF and metro/RIDE/AU."""
    for left in (a["birth"], a["work"]):
        for right in (b["birth"], b["work"]):
            if (
                left["code"] == right["code"]
                or left["uf"] == right["uf"]
                or set(left["regions"]) & set(right["regions"])
            ):
                return False
    return True
