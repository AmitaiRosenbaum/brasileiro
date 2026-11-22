#!/usr/bin/env bash

set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
project="${1:-${CLOUDFLARE_PAGES_PROJECT:-}}"
commit_hash="$(git -C "$repo_dir" rev-parse HEAD)"

if [[ -z "$project" ]]; then
  echo "Pass the Cloudflare Pages project name:" >&2
  echo "  ./scripts/deploy-frontend.sh <pages-project>" >&2
  echo "After login, list projects with: npx --yes wrangler@3 pages project list" >&2
  exit 1
fi

if ! git -C "$repo_dir" diff --quiet || ! git -C "$repo_dir" diff --cached --quiet; then
  echo "Tracked files have uncommitted changes. Commit and test them before deploying." >&2
  exit 1
fi

if ! git -C "$repo_dir" merge-base --is-ancestor HEAD origin/main; then
  echo "The current commit is not on origin/main. Push it before deploying." >&2
  exit 1
fi

cd "$repo_dir/front-end"
npm run build
if ! grep -R --fixed-strings --quiet \
  'https://api.musicbrasileiro.com/' dist/assets/*.js; then
  echo "Refusing to deploy: the built frontend does not contain the production API URL." >&2
  exit 1
fi
npx --yes wrangler@3 pages deploy dist \
  --project-name "$project" \
  --branch main \
  --commit-hash "$commit_hash"

echo "Frontend ${commit_hash:0:7} was uploaded to Cloudflare Pages."
