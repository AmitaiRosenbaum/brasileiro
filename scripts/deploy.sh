#!/usr/bin/env bash

set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
deploy_host="${DEPLOY_HOST:-oracle}"
remote_dir="${DEPLOY_REMOTE_DIR:-/home/ubuntu/brasileiro}"
image_repository="${BACKEND_IMAGE:-ghcr.io/amitairosenbaum/brasileiro-django}"
release="${1:-$(git -C "$repo_dir" rev-parse --short=7 HEAD)}"
image="${image_repository}:${release}"

if ! git -C "$repo_dir" diff --quiet || ! git -C "$repo_dir" diff --cached --quiet; then
  echo "Tracked files have uncommitted changes. Commit and test them before deploying." >&2
  exit 1
fi

if ! git -C "$repo_dir" merge-base --is-ancestor HEAD origin/main; then
  echo "The current commit is not on origin/main. Push it before deploying." >&2
  exit 1
fi

echo "Building backend image ${image}"
docker build --tag "$image" "$repo_dir/back-end"

echo "Transferring backend image to ${deploy_host}"
docker save "$image" | gzip | ssh "$deploy_host" 'gunzip | docker load'

echo "Backing up, migrating, and switching the backend"
ssh "$deploy_host" bash -s -- "$remote_dir" "$image" "$release" <<'REMOTE_SCRIPT'
set -euo pipefail

remote_dir="$1"
image="$2"
release="$3"
cd "$remote_dir"

mkdir -p backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' \
  > "backups/pre-${release}.dump"
cp docker-compose.yml "docker-compose.yml.pre-${release}"
sed -i -E "s#image: ghcr.io/amitairosenbaum/brasileiro-django:[^[:space:]]+#image: ${image}#" docker-compose.yml
docker compose run --rm backend python manage.py migrate --noinput
docker compose up -d --no-deps backend
docker compose ps backend
REMOTE_SCRIPT

echo "Waiting for the public API"
for attempt in $(seq 1 12); do
  if curl --fail --silent --show-error \
    --output /dev/null https://api.musicbrasileiro.com/auth/csrf/; then
    echo "Backend ${release} is live and healthy."
    echo "Cloudflare Pages deploys the frontend from origin/main; check its build before closing the release."
    exit 0
  fi
  if [[ "$attempt" -eq 12 ]]; then
    echo "The backend did not pass its health check. Inspect with:" >&2
    echo "  ssh ${deploy_host} 'cd ${remote_dir} && docker compose logs --tail=100 backend'" >&2
    exit 1
  fi
  sleep 5
done
