#!/usr/bin/env bash
# Deploy de demonstração do ImuniGuia em Debian (amd64) com Docker + Cloudflare Tunnel.
# Uso:  sudo ./scripts/deploy_debian.sh            -> link temporário https://*.trycloudflare.com
#       sudo PUBLIC_ORIGIN=https://app.seudominio.com ./scripts/deploy_debian.sh
#             -> use quando já houver túnel/proxy HTTPS próprio apontando para http://localhost:4173
# Não versiona nem imprime a senha do banco. Dados são sintéticos (homologação).
set -euo pipefail
cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null; then
  echo ">> Instalando Docker (script oficial)..."
  apt-get update -y && apt-get install -y curl ca-certificates
  curl -fsSL https://get.docker.com | sh
fi

if [ -z "${PUBLIC_ORIGIN:-}" ]; then
  if ! command -v cloudflared >/dev/null; then
    echo ">> Instalando cloudflared..."
    curl -fsSL -o /tmp/cloudflared.deb \
      https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
    dpkg -i /tmp/cloudflared.deb
  fi
  echo ">> Abrindo túnel temporário..."
  # Encerra somente o túnel criado por este script (outros túneis do servidor não são tocados).
  if [ -f /run/imuniguia-tunnel.pid ]; then
    kill "$(cat /run/imuniguia-tunnel.pid)" 2>/dev/null || true
  fi
  nohup cloudflared tunnel --no-autoupdate --url http://localhost:4173 >/var/log/imuniguia-tunnel.log 2>&1 &
  echo $! > /run/imuniguia-tunnel.pid
  for _ in $(seq 1 40); do
    PUBLIC_ORIGIN=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /var/log/imuniguia-tunnel.log | head -1 || true)
    [ -n "$PUBLIC_ORIGIN" ] && break
    sleep 1
  done
  [ -n "$PUBLIC_ORIGIN" ] || { echo "Não obtive o link do túnel. Veja /var/log/imuniguia-tunnel.log"; exit 1; }
fi

if [ ! -f .env ]; then
  umask 077
  printf 'POSTGRES_PASSWORD=%s\n' "$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')" > .env
fi
# Atualiza apenas as chaves de origem/cookie, preservando a senha do banco.
sed -i '/^PUBLIC_ORIGIN=/d;/^COOKIE_SECURE=/d' .env
printf 'PUBLIC_ORIGIN=%s\nCOOKIE_SECURE=true\n' "$PUBLIC_ORIGIN" >> .env

echo ">> Subindo containers (a primeira build leva alguns minutos neste hardware)..."
docker compose up --build -d
echo ">> Aguardando a API..."
for _ in $(seq 1 60); do
  docker compose ps web --format '{{.Health}}' 2>/dev/null | grep -q healthy && break
  sleep 3
done
echo
echo "ImuniGuia no ar: $PUBLIC_ORIGIN"
echo "Próximo passo:   sudo ./scripts/seed_demo.sh"
