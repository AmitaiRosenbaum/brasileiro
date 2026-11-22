# Deployment

Production has two independently deployed parts:

- The React frontend is uploaded to Cloudflare Pages with Wrangler.
- The Django backend and PostgreSQL database run on the Oracle server configured
  as the `oracle` SSH host.

## Normal release

From the repository root:

```bash
# 1. Verify the change locally.
cd front-end
npm run lint
npm run build
cd ../back-end
UV_CACHE_DIR=/tmp/brasileiro-uv-cache uv run python songAPI/manage.py test songAPI.songs
cd ..

# 2. Commit and push.
git add <the files you changed>
git commit -m "describe the release"
git push origin main

# 3. Deploy the matching backend commit to Oracle.
./scripts/deploy.sh

# 4. Deploy the matching frontend commit to Cloudflare Pages.
./scripts/deploy-frontend.sh <pages-project>
```

The script refuses to deploy uncommitted tracked changes or a commit that is not
on `origin/main`. It then:

1. tags the backend image with the Git commit;
2. transfers it directly to Oracle (so GHCR authentication is not required);
3. creates a timestamped-by-release PostgreSQL backup;
4. saves the previous Compose file;
5. runs migrations in a one-off container;
6. switches only the backend container; and
7. checks the public HTTPS API.

The generated `pdf-processing-engine/src/music/songs.zip` is intentionally not
part of an application deployment.

### First frontend deployment on a new computer

Authorize Wrangler once in your browser:

```bash
cd front-end
npx --yes wrangler@3 login
npx --yes wrangler@3 pages project list
```

Use the project name from that list with `deploy-frontend.sh`. You can store it
for future terminals instead of passing it each time:

```bash
export CLOUDFLARE_PAGES_PROJECT=<pages-project>
./scripts/deploy-frontend.sh
```

Wrangler 3 is pinned in this command because this workstation currently uses
Node 18; current Wrangler 4 releases require a newer Node version. No Cloudflare
password or API token belongs in this repository.

The non-secret production API address is committed in
`front-end/.env.production`. The frontend deployment script verifies that the
built JavaScript contains `https://api.musicbrasileiro.com/` and refuses to
upload a broken same-origin build.

## Verify the release

Check the Cloudflare Pages build in its dashboard, then open:

- <https://musicbrasileiro.com/>
- <https://api.musicbrasileiro.com/auth/csrf/>

On Oracle, confirm the exact backend image and recent logs:

```bash
ssh oracle
cd /home/ubuntu/brasileiro
docker compose ps backend
docker compose logs --tail=100 backend
```

## Roll back the backend

Every release leaves both `docker-compose.yml.pre-<release>` and
`backups/pre-<release>.dump` on Oracle. To roll back application code without
rolling back data:

```bash
ssh oracle
cd /home/ubuntu/brasileiro
cp docker-compose.yml.pre-<release> docker-compose.yml
docker compose up -d --no-deps backend
```

Database restoration is a separate, destructive operation. Use it only when a
migration or data write must be reversed, and preserve the current database
before restoring an older dump.
