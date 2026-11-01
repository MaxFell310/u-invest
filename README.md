# U-Invest MVP

U-Invest is a static Ukrainian-language product concept with a FastAPI API for
an A/B headline experiment, anonymous feedback, aggregate reporting, a private
collaborator dashboard, and a user-owned demo portfolio. Portfolio balances and
trades are virtual only; the app does not execute financial transactions or
provide investment recommendations.

## Architecture

- `index.html`, `styles/style.css`, and `script.js` preserve the public static
  website. `login.html`, `register.html`, `reset-password.html`, and
  `profile.html` provide the Supabase Auth and virtual portfolio flows.
  `admin.html` and `admin.js` provide the separate protected team dashboard.
- The existing `uv` project at the repository root builds the
  `src/u_invest` package; there is no second Python project.
- `src/u_invest/main.py` configures FastAPI and registers the `/api` routers.
  `database.py` handles SQLAlchemy engines; `config.py` reads environment
  configuration; `dependencies.py` provides request-scoped sessions and
  collaborator authorization.
- `models/` and `schemas/` organize SQLAlchemy models and Pydantic
  request/response types by domain. `routers/` implements API endpoints,
  `services/` contains analytics, token verification, and CSV logic, and
  `migrations/` contains Alembic revisions.
- Local development uses SQLite. Production is configured for hosted
  PostgreSQL using psycopg. Supabase Auth issues user tokens; each portfolio
  request is scoped to the verified JWT subject. Raw feedback and CSV
  endpoints remain restricted to the separate team UUID allowlist.
- Public survey submissions do not request names, email, IP addresses, or
  browser fingerprints. Supabase Auth serves both public user accounts and
  team accounts, with backend authorization kept separate.

Technologies: Python 3.14+, FastAPI, Pydantic, SQLAlchemy 2.0, Alembic,
PostgreSQL/psycopg, optional SQLite, Supabase Auth, vanilla HTML/CSS/JavaScript,
`uv`, and pytest.

## Local setup

From the repository root:

```powershell
uv sync --group dev
Copy-Item .env.example .env
uv run --env-file .env alembic upgrade head
```

`.env.example` selects `sqlite:///./u_invest.db` by default. `.env` and the
database file are excluded from Git. Tables are created by migrations, not
automatically at app startup. `U_INVEST_DATABASE_URL` can be a local SQLite URL
or a PostgreSQL URL; production requires PostgreSQL.

Start the backend from the project root with the requested FastAPI CLI command:

```powershell
uv run fastapi dev src/u_invest/main.py
```

The server listens on `http://127.0.0.1:8000`. To load `.env` values into the
development process, use:

```powershell
uv run --env-file .env fastapi dev src/u_invest/main.py
```

The existing configured console entry point remains available with
`uv run --env-file .env u-invest`. Start the existing frontend from another
PowerShell window:

```powershell
python -m http.server 5500 --bind 127.0.0.1
```

Open `http://127.0.0.1:5500/`. If the API is unavailable, the public landing
page and browser-local interactions remain usable; API-backed functionality
shows an availability message.

## FastAPI, Swagger UI, and routes

FastAPI's interactive Swagger UI is at
`http://127.0.0.1:8000/docs`; OpenAPI JSON is at
`http://127.0.0.1:8000/openapi.json`; ReDoc is at
`http://127.0.0.1:8000/redoc`. API routes use `/api`. Endpoint schemas,
examples, and validation/authentication errors appear in the documentation.
Public endpoints can be executed in Swagger. Portfolio endpoints accept any
valid Supabase user access token; the admin and full analytics export endpoints
require an allowlisted collaborator token.

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Checks database connectivity and verifies that all model tables exist |
| `POST` | `/api/experiments/assign` | Creates or returns a stable visitor assignment |
| `POST` | `/api/analytics/events` | Records an allowed page view or CTA click |
| `POST` | `/api/feedback` | Validates and stores anonymous survey feedback |
| `GET` | `/api/analytics/summary` | Returns aggregate experiment/feedback metrics |
| `GET` | `/api/analytics/sustainability` | Returns submitted environmental/social/ethical distributions |
| `GET` | `/api/admin/feedback` | Protected paginated responses with search/filter parameters |
| `GET` | `/api/admin/feedback/summary` | Protected feedback and sustainability statistics |
| `GET` | `/api/admin/feedback/export` | Protected feedback-only CSV |
| `GET` | `/api/analytics/export` | Protected full research CSV, including anonymous visitor IDs |
| `GET` | `/api/exchange-rates` | Cached USD/EUR cash rates from PrivatBank; returns stale data or HTTP 503 when unavailable |
| `GET` | `/api/profile` | Authenticated user's profile, refreshed from verified Supabase JWT claims |
| `GET` | `/api/portfolio` | Authenticated user's demo balance, positions, and virtual account value |
| `GET` | `/api/portfolio/transactions` | Authenticated user's recent virtual transaction history |
| `POST` | `/api/portfolio/demo-deposits` | Idempotently adds virtual demo funds; no payment is made |
| `POST` | `/api/portfolio/trades` | Idempotently records a virtual buy or sell using an explicitly entered demo price |

`/api/feedback` only accepts new validated responses; there is no public
feedback-list endpoint. Raw comments and CSV exports are restricted to
authorized collaborators. CSV responses use `Cache-Control: no-store`.

All portfolio routes require `Authorization: Bearer <Supabase access token>`.
The server verifies the token's issuer, audience, signature, expiration, and
UUID subject, and derives ownership exclusively from that subject (never from
frontend `user_id`). Database operations use PostgreSQL row locks and a unique
per-user `request_id`; insufficient demo cash or shares are rejected atomically.
The account starts at USD 0.00. The demo deposit action only credits virtual
funds. Demo trade prices are entered by the user and are not market quotes;
portfolio valuation is based on invested cost only, with no unrealized return.

The exchange-rate endpoint fetches PrivatBank's cash-rate API with a five
second timeout, validates both UAH-base USD and EUR rates, and caches successful
results for ten minutes. If a refresh fails, the last successful response is
returned with `stale: true`; without a cached response the endpoint returns
HTTP 503. These rates are never used as stock prices.

## Database and migrations

The application selects its database from `U_INVEST_DATABASE_URL`. SQLite is
for local development and automated tests. The production database should be
the hosted Supabase PostgreSQL database, not a local file on an ephemeral
backend host. For PostgreSQL, use the SQLAlchemy psycopg scheme
`postgresql+psycopg://`; legacy `postgresql://` and `postgres://` prefixes are
normalized by the application. In production, the app requires PostgreSQL and
adds `sslmode=require` if it is missing. `pool_pre_ping` and connection recycle
are enabled; Supabase pooler hosts disable psycopg prepared statements.

Alembic revision `8a32f6d1c907_add_user_demo_portfolios` adds the tables
`user_profiles`, `demo_wallets`, `portfolio_positions`, and
`portfolio_transactions`. It does not alter the applied initial revision.
Amounts use `Numeric`/`Decimal`; every portfolio row is keyed by the verified
Supabase Auth UUID. FastAPI is the only database access path for these records,
so no browser-side Supabase Data API/RLS access is used. Do not apply this
revision to production until the migration is explicitly approved.

Apply migrations before starting the API:

```powershell
uv run --env-file .env alembic upgrade head
```

The health endpoint returns HTTP 503 with the migration command if required
tables are missing. It does not create or alter the database schema.

### Initialize a new production database

After setting `U_INVEST_DATABASE_URL` to the Supabase PostgreSQL connection URL
and `U_INVEST_ENV=production` in the deployment environment, run this once from
the repository root:

```powershell
uv run alembic upgrade head
```

For a local PowerShell terminal using a private, ignored `.env` file containing
the production database URL, explicitly select production mode without putting
the URL in the command or source code:

```powershell
$env:U_INVEST_ENV = "production"
uv run --env-file .env alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }
Remove-Item Env:U_INVEST_ENV
```

This applies pending Alembic revisions to the database selected by
`U_INVEST_DATABASE_URL`; it is safe to rerun and does not drop tables or clear
rows. Do not run it until the URL is configured for the intended database.
Keep the URL in the ignored `.env` file or the host's secret environment
settings, and do not paste it into logs or screenshots.

To check that every table registered by the SQLAlchemy models exists in that
same database without printing its connection URL:

```powershell
$env:U_INVEST_ENV = "production"
uv run --env-file .env python -c "from sqlalchemy import inspect; from u_invest.database import engine; from u_invest.models import Base; present=set(inspect(engine).get_table_names()); missing=set(Base.metadata.tables)-present; print('Database schema: OK' if not missing else f'Missing tables: {sorted(missing)}'); raise SystemExit(bool(missing))"
if ($LASTEXITCODE -ne 0) { throw "Database schema check failed." }
Remove-Item Env:U_INVEST_ENV
```

When the API is running, `GET /api/health` provides the same schema-readiness
check and returns HTTP 200 only when the database is reachable and all model
tables exist. A missing table returns HTTP 503; run the migration command above
against the same database URL configured for Render.

Inspect the current migration:

```powershell
uv run --env-file .env alembic current
```

Create future revisions after changing SQLAlchemy models:

```powershell
uv run --env-file .env alembic revision --autogenerate -m "describe schema change"
```

Review generated migration code before applying it. Run migrations as a
deployment/release step before serving application traffic. A database made by
an older `create_all` build has no Alembic revision marker: back it up and
verify its schema before considering `alembic stamp head`; never stamp an
unknown or empty schema. Moving any existing SQLite data to PostgreSQL requires
a separate backup and data migration, not merely changing the database URL.

## Anonymous feedback and collaborator dashboard

The survey collects an optional rating from 1–5, investment-interest answer,
optional comment (up to 1,000 characters), and environmental, social, and
ethical importance responses. Inputs are validated in Pydantic and guarded by
database constraints. Submitted survey records do not contain a visitor ID.
Dashboard responses are paginated newest-first, with comment search and
rating/interest/sustainability filters available from the API. The page shows
submission time, rating, interest, comment, all three sustainability answers,
aggregated counts, and a CSV export.

### Supabase Auth users and team permissions

1. Configure email delivery and enable email/password sign-up for ordinary
   users. Keep email confirmation enabled; do not disable Supabase confirmation
   to simplify testing.
2. Keep the existing team workflow: in **Supabase → Authentication → Users**,
   invite each collaborator to their own address. They sign in to `admin.html`
   using the existing emailed Magic Link.
3. Copy each invited user's Auth UUID. Set backend environment variable
   `U_INVEST_ADMIN_USER_IDS` to the comma-separated UUIDs authorized to read
   feedback, then deploy/restart the API. This list is for team access only;
   ordinary registration never adds a user to it.
4. `api-config.js` contains the public Supabase project URL and publishable
   key used by the shared `supabase-config.js` client. These are public client
   settings, not secrets. Never put the database password, service-role key,
   JWT signing secret, or other administrative secret in frontend code.
5. In **Supabase → Authentication → URL Configuration → Redirect URLs**, add:
   - `https://maxfell310.github.io/u-invest/login.html`
   - `https://maxfell310.github.io/u-invest/reset-password.html`
   - `https://maxfell310.github.io/u-invest/admin.html`
   - `http://127.0.0.1:5500/login.html`
   - `http://127.0.0.1:5500/reset-password.html`
   - `http://127.0.0.1:5500/admin.html`

The API verifies the token's signature against Supabase's published JWKS and
checks issuer, audience, and the JWT `sub` UUID. Configure Supabase Auth to
issue asymmetric ES256 or RS256 tokens for JWKS verification. Portfolio access
allows any valid authenticated user but only exposes data owned by that
verified subject. The admin API additionally requires the team allowlist;
`admin.js` continues using `signInWithOtp({ shouldCreateUser: false })`.

Git repository permissions and feedback access are separate. A collaborator
who only needs research results gets an individual Supabase Auth account and
an allowlisted UUID; they do not need GitHub repository access or the database
password. The project owner grants/revokes access in Supabase Auth and the
backend host's environment settings. Do not share production database
credentials with read-only collaborators.

## A/B experiment and analytics

The experiment compares these exact hero headlines:

- Variant A: **Invest in Ukraine's Future**
- Variant B: **Discover Investment Opportunities in Ukraine**

On the first API-backed visit, the server randomly assigns A or B with
`secrets.choice` and stores a unique assignment per browser UUID and
experiment. The browser stores a random UUID in `localStorage` and reuses it
for returning visits. Page views and primary CTA clicks are recorded. Repeated
clicks count as multiple events but only one visitor conversion. Conversion
rate is unique assigned visitors with one or more CTA clicks divided by
assigned visitors in that variant. With no assigned visitors, the rate is
zero.

The server stores A/B assignments and analytics events in the configured
database. The anonymous `/api/feedback` survey separately stores its optional
1–5 experience rating, investment-interest answer, environmental/social/ethical
answers, optional comment, and submission timestamp; it does not store the A/B
visitor ID. The older page-rating widget, reactions, feature-poll votes, and
comments are stored only in that visitor's browser `localStorage`. They are
not sent to the server and are not synchronized across browsers or users.
Moving those older interactions to shared results would require separate API
and database work.

Assignments and client-submitted events can be manipulated. Clearing browser
storage or using another device can create another identifier; there is no
fingerprinting, account verification, or reliable bot detection. Counts
represent browser IDs/events, not verified people. Small or self-selected
samples do not establish reliable causal conclusions, and statistical
significance is not calculated. Report actual dates and counts; do not claim a
winning headline if evidence is insufficient. Use the blank
[assessment report template](./REPORT_TEMPLATE.md) after collecting real data;
do not fabricate participants, findings, or conclusions.

## Frontend configuration and CORS

Frontend pages load the shared `api-config.js` and singleton
`supabase-config.js`. `api-config.js` selects the local API
(`http://127.0.0.1:8000`) only when served from `localhost`, `127.0.0.1`, or
`[::1]`; all other hosts use `https://u-invest-fastapi.onrender.com`. No API
URL is duplicated in the HTML pages. The Supabase publishable key is public
and does not grant administrative API access; the service-role key is never
used by the frontend.

Local CORS defaults are `http://localhost:5500` and
`http://127.0.0.1:5500`. Set production
`U_INVEST_CORS_ORIGINS=https://maxfell310.github.io` on the backend. The API
allows `Authorization` for authenticated user and team requests but does not enable cookie
credentials. Never use wildcard CORS. CORS is not authentication.

## Production deployment

The intended deployment is GitHub Pages for the static frontend, a separate
HTTPS-capable Python host for FastAPI, and hosted PostgreSQL in Supabase.
Configure host-provided environment variables/secrets; do not commit `.env` or
production URLs with credentials. `.env.example` contains placeholders only.

Example backend variables (use the actual values provided by your services):

```text
U_INVEST_ENV=production
U_INVEST_HOST=0.0.0.0
U_INVEST_PORT=<port-required-by-the-host>
U_INVEST_DATABASE_URL=postgresql+psycopg://<user>:<password>@<host>:<port>/<database>?sslmode=require
U_INVEST_CORS_ORIGINS=https://maxfell310.github.io
SUPABASE_URL=https://<project-ref>.supabase.co
U_INVEST_ADMIN_USER_IDS=<invited-user-uuid>[,<another-user-uuid>]
```

Use the PostgreSQL URI from Supabase's **Connect** panel. A Supabase
transaction-pooler URI may be used when required by the backend host; include
SSL and use the exact host/port/database supplied by Supabase. On the backend
host, configure the variables using its persistent environment/secrets
settings, apply `uv run alembic upgrade head` as a release step, and run
`uv run u-invest` (or the host's equivalent start command). Ensure the host
routes HTTPS to FastAPI.

The API base requires no per-deployment edit: `api-config.js` selects Render
for GitHub Pages and localhost for local development. Verify the centralized
public Supabase URL and publishable key in `api-config.js` match the intended
project, configure the redirect URLs, and invite the authorized collaborators
as described above. No production Auth setting or database migration was
changed by this code update.

The deployed Render API was checked for health, aggregate reads, OpenAPI
routes, and CORS preflight; protected feedback routes correctly rejected
requests without a token. A production feedback submission and retrieval by an
authorized collaborator were not performed during this verification to avoid
adding test data or using collaborator credentials. Verify those workflows
with an explicitly identified test submission and invited collaborator before
claiming end-to-end production verification.

## Testing

Run the isolated backend suite:

```powershell
uv run --group dev pytest -q
```

Tests use isolated SQLite databases and mock Supabase token verification; they
do not require production credentials or modify `u_invest.db`.
