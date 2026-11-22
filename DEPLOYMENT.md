# Deployment

Production has two independently deployed parts:

- The React frontend is built by Cloudflare Pages from `main`.
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

# 2. Commit and push. Pushing main starts the Cloudflare frontend build.
git add <the files you changed>
git commit -m "describe the release"
git push origin main

# 3. Deploy the matching backend commit to Oracle.
./scripts/deploy.sh
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
