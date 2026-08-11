# Contributing to Manar QC

Welcome to the Manar QC project. This is a production codebase — read this guide fully before writing a single line.

---

## 1. What This Project Is

**Manar QC** (`qcg.manar.pk`) is an offline, calibrated 2D dimensional-control instrument for Pakistan's export textile sector.

- **Portal** — Multi-tenant Django 5 app. Buyers, styles, spec matrices, signed station packs.
- **Station** — Offline Python app running on factory Linux PCs. Overhead camera + ArUco homography.

The live site: **https://qcg.manar.pk** (HTTPS, TLS via Let's Encrypt, behind Traefik on the Manar VPS).

---

## 2. Codebase Layout

```
manar-qc/
├── qc/                         # Django project root
│   ├── manage.py
│   ├── qc/                     # settings, urls, wsgi, asgi
│   └── core/                   # single Django app
│       ├── models.py           # all DB models (User, Tenant, Style, WorkOrder, Pack…)
│       ├── views.py            # all portal views
│       ├── forms.py
│       ├── packs.py            # pack signing/verification (Ed25519 via PyNaCl)
│       ├── sheets.py           # T-1100 / U-1400 / SHOE-600 calibration profiles
│       ├── permissions.py      # role decorators (portal_admin, buyer_admin, operator)
│       ├── auth_views.py       # login / token activate / SSO
│       ├── sso.py              # OIDC SSO (optional, flag-gated)
│       ├── admin.py
│       ├── imports.py          # measurement library CSV importer
│       ├── templates/          # 14 Jinja-adjacent templates
│       ├── static/             # manar.css + htmx.min.js
│       └── management/commands/
│           ├── genkeys.py      # generate Ed25519 keypair
│           ├── load_library.py # seed measurement library
│           ├── seed_demo.py    # seed demo tenant/styles
│           ├── make_bootstrap.py
│           └── bootstrap.py
├── station/                    # offline station app (shipped as .mpk)
│   └── station/
│       ├── main.py             # CLI entrypoint
│       ├── vision.py           # ArUco detection & homography
│       ├── drift.py            # calibration drift
│       ├── packs.py            # pack load/verify
│       ├── store.py            # SQLite measurement store
│       ├── auth.py             # pin auth
│       ├── export.py
│       ├── pdf_report.py
│       ├── validate.py
│       └── ui.py               # Tkinter kiosk UI
├── docs/                       # architecture, runbook, security, pilot guide
├── deploy/                     # systemd service, backup script
├── docker-compose.yml          # VPS deployment (web + postgres + redis)
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

## 3. Getting Started (Local Dev)

### Prerequisites
- Docker + Docker Compose
- Python 3.12+ (for local runs without Docker)
- `gh` CLI (optional, for PR workflows)

### First-time setup

```bash
git clone git@github.com:Manar-Soverign-Systems/manar-qc.git
cd manar-qc

cp .env.example .env
# .env is gitignored. Fill in values as needed for local dev.
# For local dev: DEBUG=1, POSTGRES_PASSWORD=devpass is fine.

docker compose up -d db redis
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py load_library
docker compose run --rm web python manage.py seed_demo
docker compose run --rm web python manage.py createsuperuser
docker compose up -d
```

Visit: http://localhost:8000

---

## 4. Branching & PR Rules

| Branch | Purpose |
|--------|---------|
| `main` | Production. Deployed to `qcg.manar.pk`. Never push directly. |
| `dev` | Integration. All feature branches merge here first. |
| `feat/<name>` | Feature work. Branch off `dev`. |
| `fix/<name>` | Bug fixes. Branch off `dev` (or `main` for hotfixes). |

### PR Checklist
- [ ] `docker compose run --rm web python manage.py test core` passes
- [ ] No secrets / `.env` values committed
- [ ] Migrations included if models changed (`makemigrations`)
- [ ] PR description explains **what** changed and **why**
- [ ] One approval from `@farabibinimran-beep` before merge

---

## 5. Commit Style

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add SHOE-600 sheet calibration profile
fix: correct argon2 hasher ordering in settings
docs: update runbook VPS deployment steps
test: add pack signing round-trip test
```

---

## 6. Key Concepts You Must Understand

### Sheets
Three calibration reference sheets exist:
- **T-1100** — 1100×900 mm cutting table sheet (12 markers, IDs 0-11)
- **U-1400** — 1400×1100 mm larger table sheet (16 markers, IDs 20-35)
- **SHOE-600** — 600×500 mm shoe/small-part sheet (8 markers, IDs 40-47)

All geometry is defined in `core/sheets.py`.

### Packs
A **Pack** is a signed JSON bundle (`.mpk`) issued by the portal to a station. It contains:
- Style specs (measurements + tolerances)
- Work order ID and batch info
- Ed25519 signature from the portal's signing key

Station software verifies the signature before accepting a pack. See `core/packs.py` and `station/station/packs.py`.

### Roles
| Role | What they can do |
|------|-----------------|
| `superuser` | Full access, tenant management |
| `portal_admin` | Manage their tenant's buyers, styles, work orders |
| `buyer_admin` | View/manage their buyer's styles |
| `operator` | Issue packs, view work orders |

Enforced via decorators in `core/permissions.py`.

---

## 7. Tests

```bash
# Portal tests
docker compose run --rm web python manage.py test core

# Station tests (no Docker needed)
cd station
python -m pytest station/tests.py -v
```

---

## 8. Secrets & Security

- **Never commit** `.env`, `*.key`, `*.pub`, or `secrets/` to git (`.gitignore` covers this)
- Ed25519 keypairs are generated with `python manage.py genkeys /secrets`
- On the VPS, secrets live in `/secrets/` (mounted as Docker volume)
- Ask Farabi for access to `vault.manar.pk` (Infisical) for shared credentials

---

## 9. Who to Ask

| Question | Contact |
|----------|---------|
| Architecture, product decisions | Farabi (`founder@manar.pk`) |
| VPS access, deployment | Farabi |
| Code review, PR approval | Farabi |

---

## 10. Useful Links

| Resource | URL |
|----------|-----|
| Live Portal | https://qcg.manar.pk |
| Architecture Doc | `docs/ARCHITECTURE_v2.md` |
| Runbook | `docs/RUNBOOK.md` |
| Security Policy | `docs/SECURITY.md` |
| Pilot Guide | `docs/PILOT.md` |
| Pack Spec | `docs/PACK_SPEC.md` |
