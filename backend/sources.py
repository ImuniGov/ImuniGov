"""Public RNDS terminology only: never sends patient data or activates clinical rules."""

import hashlib
import json
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Request

from .domain import now
from .security import session_user

URL = "https://fhir.saude.gov.br/ria/pt-BR/CodeSystem-BRImunobiologico.json"
SYSTEM = "http://www.saude.gov.br/fhir/r4/CodeSystem/BRImunobiologico"
BUNDLED = Path(__file__).parent / "references" / "rnds-vaccines.json"
router = APIRouter()
ALIASES = {
    "15": "BCG",
    "42": "Pentavalente",
    "22": "Poliomielite VIP",
    "9": "Hepatite B",
    "26": "Pneumocócica 10",
    "39": "Rotavírus humano",
    "41": "Meningocócica C",
    "14": "Febre amarela",
    "24": "Tríplice viral",
    "35": "Hepatite A",
    "47": "DTP",
    "56": "Tetraviral",
    "37": "Varicela",
}


def normalize(raw):
    data = json.loads(raw)
    if data.get("resourceType") != "CodeSystem" or data.get("url") != SYSTEM:
        raise ValueError("Resposta não corresponde ao catálogo RNDS esperado.")
    items = []
    seen = set()
    for item in data.get("concept", []):
        props = {p["code"]: p.get("valueBoolean", p.get("valueString")) for p in item.get("property", [])}
        if props.get("Category") != "Vacina" or props.get("inactive") is True:
            continue
        code, display = str(item["code"]), item["display"]
        if (
            code in seen
            or not code.isdecimal()
            or not isinstance(display, str)
            or not 1 <= len(display) <= 80
        ):
            raise ValueError("Código ou nome inválido no catálogo.")
        seen.add(code)
        items.append(
            {
                "code": code,
                "name": ALIASES.get(code, display),
                "display": display,
                "description": props.get("Name", item.get("definition", display)),
            }
        )
    if not items:
        raise ValueError("Catálogo não contém vacinas ativas.")
    return {
        "source": URL,
        "system": SYSTEM,
        "version": data.get("version"),
        "publishedAt": data.get("date"),
        "checkedAt": now(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "items": items,
    }


def read_catalog(data_dir):
    cached = Path(data_dir) / "references" / "rnds-vaccines.json"
    try:
        result = json.loads(cached.read_text(encoding="utf-8"))
        if result["source"] != URL or not result["items"]:
            raise ValueError("Cópia inválida")
        return result
    except (OSError, ValueError, KeyError):
        return json.loads(BUNDLED.read_text(encoding="utf-8"))


def sync_catalog(data_dir):
    directory = Path(data_dir) / "references"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            with client.stream("GET", URL, headers={"Accept": "application/json"}) as response:
                response.raise_for_status()
                raw = bytearray()
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 5_000_000:
                        raise ValueError("Catálogo excedeu o limite.")
        result = normalize(bytes(raw))
        temporary = directory / "rnds-vaccines.tmp"
        temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(directory / "rnds-vaccines.json")
        status = {"ok": True, "attemptedAt": now(), "error": ""}
    except (httpx.HTTPError, OSError, ValueError, KeyError, TypeError):
        status = {
            "ok": False,
            "attemptedAt": now(),
            "error": "Não foi possível atualizar. A última referência disponível foi preservada.",
        }
    (directory / "status.json").write_text(json.dumps(status), encoding="utf-8")
    return status


@router.get("/api/v1/vaccine-catalog")
def vaccine_catalog(request: Request, user=Depends(session_user)):
    result = read_catalog(request.app.state.data)
    try:
        result["lastUpdate"] = json.loads((request.app.state.data / "references" / "status.json").read_text())
    except (OSError, ValueError):
        result["lastUpdate"] = None
    return result
