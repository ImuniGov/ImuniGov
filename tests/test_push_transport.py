import base64
import os

import pywebpush
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from backend.push import ensure_keys


def test_webpush_generates_encrypted_payload_and_vapid_signature(tmp_path, monkeypatch):
    key = ec.generate_private_key(ec.SECP256R1())
    public = key.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )

    def encode(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

    subscription = {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test-synthetic",
        "keys": {"p256dh": encode(public), "auth": encode(os.urandom(16))},
    }
    calls = []

    def post(endpoint, **kwargs):
        calls.append((endpoint, kwargs))
        response = requests.Response()
        response.status_code = 202
        response._content = b""
        return response

    monkeypatch.setattr(pywebpush.requests, "post", post)
    pywebpush.webpush(
        subscription_info=subscription,
        data='{"type":"care-update"}',
        vapid_private_key=str(ensure_keys(tmp_path)),
        vapid_claims={"sub": "https://localhost"},
        timeout=10,
        ttl=86400,
    )
    assert len(calls) == 1
    endpoint, request = calls[0]
    assert endpoint == subscription["endpoint"]
    assert request["headers"]["authorization"].startswith("vapid ")
    assert request["headers"]["content-encoding"] == "aes128gcm"
    assert b"care-update" not in request["data"]
