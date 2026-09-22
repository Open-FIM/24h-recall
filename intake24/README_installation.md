# Installation instructions

## 1.Install and run Intake24
Official Intake24 docs:
Overview: https://docs.intake24.org/
Getting started: https://docs.intake24.org/guide/get-started
Docker development setup: https://docs.intake24.org/guide/docker
Clone and set up Intake24 separately (it is not vendored in this repository):
```bash
git clone https://github.com/intake24/intake24
cd intake24
pnpm install
docker compose up -d # PostgreSQL + Redis
pnpm cli init:env # first-time setup
pnpm cli init:db:system # first-time setup (creates admin user)
pnpm db:migrate
```
Start Intake24 admin (and required API)
Admin depends on the API. From the Intake24 repo:
```bash
Terminal 1 — API (default http://localhost:3100)
cd apps/api && pnpm dev
Terminal 2 — Admin tool (default http://localhost:8100)
cd apps/admin && pnpm dev
```
Open the admin tool at http://localhost:8100 and sign in with the admin account created during `pnpm cli init:db:system`.
Optionally start the participant survey UI as well:
```bash
Terminal 3 — Survey (default http://localhost:8200)
cd apps/survey && pnpm dev
```
After Intake24 is running, note:
the admin URL (for example `http://localhost:8100`)
the public Intake24 survey base URL (for example `http://localhost:8200`)
your survey slug
the JWT secret used by Intake24 (needed for participant link generation)
Use the admin panel to create/configure surveys, set locales (including `en_US` after FNDDS import), and manage food data.
For US food mapping and optional FNDDS import steps, see [`intake24/README.md`](intake24/README.md).

## 2. Start the OpenFIM recall webhook and database
From this repository:
```bash
cp docker-compose.example.yml docker-compose.yml
```
Edit `docker-compose.yml` and set at least:
`INTAKE24_URL` — your Intake24 base URL
`SURVEY_ID` — your Intake24 survey slug
`JWT_SECRET` — must match Intake24
database passwords for local use
Then start services:
```bash
docker compose up -d
```
This starts:
PostgreSQL recall database on port `5433`
Flask webhook on port `5000`
The recall tables are created automatically from `sql/create_recall_tables.sql`.

## 3. Install the OpenWebUI Intake24 pipeline
The OpenWebUI pipeline lives at:
pipelines/openfim_recall_pipeline.py
Install it in OpenWebUI Pipelines (Admin → Pipelines), or copy it into your pipelines volume/directory.
Configure pipeline valves / environment as needed:
`WEBHOOK_INTERNAL_BASE` — URL the pipeline uses to reach the webhook (for example `http://host.docker.internal:5000` from a Docker pipelines container, or `http://localhost:5000` locally)
`INTAKE24_URL` — public Intake24 base URL returned to users
Example prompts after installation:
`start baseline recall for P001`

## 4. Point Intake24 callbacks at the webhook
Configure your Intake24 survey / integration so completed recalls POST to:
Http://<webhook-host>:5000/intake24/callback
