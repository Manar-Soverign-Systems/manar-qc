# MANAR QC — Dimensional Control System (v2.0)

**Manar QC** is an offline, portable, calibrated 2D dimensional-control instrument for Pakistan's export textile sector (`manar.pk`).

## Architecture
- **Portal** (`qcg.manar.pk`): Multi-tenant Django 5 portal for managing buyers, styles, spec matrices, signed station packs, and opt-in aggregates.
- **Station**: Offline Linux PC companion app for overhead camera garment / cut-panel measurement with ArUco sheet homography.

## Quickstart
```bash
cp .env.example .env
docker compose up -d db redis
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py load_library
docker compose run --rm web python manage.py seed_demo
docker compose up -d
```
