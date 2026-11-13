import json

import httpx
import pytest

from backend import sources


def test_official_catalog_filters_non_vaccines_and_inactive():
    raw = json.dumps(
        {
            "resourceType": "CodeSystem",
            "url": sources.SYSTEM,
            "version": "test",
            "concept": [
                {"code": "15", "display": "BCG", "property": [{"code": "Category", "valueString": "Vacina"}]},
                {"code": "1", "display": "Soro", "property": [{"code": "Category", "valueString": "Soro"}]},
                {
                    "code": "2",
                    "display": "Antiga",
                    "property": [
                        {"code": "Category", "valueString": "Vacina"},
                        {"code": "inactive", "valueBoolean": True},
                    ],
                },
            ],
        }
    ).encode()
    result = sources.normalize(raw)
    assert [i["code"] for i in result["items"]] == ["15"] and len(result["sha256"]) == 64
    with pytest.raises(ValueError):
        sources.normalize(b'{"resourceType":"Patient"}')


def test_failed_refresh_keeps_official_copy_and_never_activates_rules(env, monkeypatch):
    engine, root, app, client = env
    previous = sources.read_catalog(root)

    class Offline:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            raise httpx.ConnectError("offline")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(sources.httpx, "Client", Offline)
    assert not sources.sync_catalog(root)["ok"]
    assert sources.read_catalog(root) == previous
    response = client().get("/api/v1/vaccine-catalog")
    assert response.status_code == 200 and response.json()["source"] == sources.URL
    assert not response.json()["lastUpdate"]["ok"]
    assert all("code" in item for item in response.json()["items"])
