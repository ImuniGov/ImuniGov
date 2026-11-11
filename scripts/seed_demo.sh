#!/usr/bin/env bash
# Cria contas SINTÉTICAS de demonstração no stack Docker em execução.
# Senha única de demonstração (altere DEMO_PASSWORD se quiser). Não usar com dados reais.
set -euo pipefail
cd "$(dirname "$0")/.."
PASS="${DEMO_PASSWORD:-SenhaForte123!}"
RUN=(docker compose exec -T -e DEMO_PASSWORD="$PASS" web)

"${RUN[@]}" python - <<'PY'
import os
from sqlalchemy import select
from backend import db
from backend.manage import create_user
from backend.privacy import Acceptance, policy, record_acceptance

pwd = os.environ["DEMO_PASSWORD"]
accounts = [
    ("familia@exemplo.br", "Maria Família (Demo)", "familia"),
    ("ubs1@exemplo.br", "Dra. Ana Souza (UBS SP)", "ubs"),
    ("ubs2@exemplo.br", "Dr. Bruno Lima (UBS RJ)", "ubs"),
    ("ubs3@exemplo.br", "Enf. Carla Mendes (UBS MT)", "ubs"),
    ("ubs4@exemplo.br", "Dr. Diego Rocha (UBS PR)", "ubs"),
    ("acs@exemplo.br", "João Agente Comunitário (ACS)", "acs"),
]
engine = db.make_engine()
for email, name, role in accounts:
    with engine.connect() as con:
        exists = con.scalar(select(db.users.c.id).where(db.users.c.email == email))
    if not exists:
        create_user(email, name, role, pwd)
with engine.begin() as con:
    fam = con.scalar(select(db.users.c.id).where(db.users.c.email == "familia@exemplo.br"))
    if not con.scalar(select(db.acceptances.c.id).where(db.acceptances.c.user_id == fam)):
        p = policy()
        record_acceptance(
            con,
            fam,
            Acceptance(
                consent=True,
                healthConsent=True,
                adultDeclaration=True,
                termsVersion=p["version"],
                privacyHash=p["hash"],
            ),
        )
PY

verify() {
  "${RUN[@]}" python -m backend.manage verify-reviewer --email "$1" --professional-id "$2" \
    --birth-city "$3" --work-city "$3" --verification-ref "DEMO-$2" || echo "(já verificado: $1)"
}
verify ubs1@exemplo.br COREN-SP-1001 3550308
verify ubs2@exemplo.br COREN-RJ-2002 3304557
verify ubs3@exemplo.br COREN-MT-3003 5103403
verify ubs4@exemplo.br COREN-PR-4004 4106902

echo
echo "Contas criadas (senha: $PASS):"
echo "  familia@exemplo.br | ubs1..ubs4@exemplo.br | acs@exemplo.br"
