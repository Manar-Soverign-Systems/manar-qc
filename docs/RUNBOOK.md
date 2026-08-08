# MANAR QC — Operations & Deployment Runbook

## 1. VPS Portal Deployment (`qcg.manar.pk`)

### Step 1: Environment Setup
```bash
git clone git@github.com:manar/manar-qc.git /opt/manar-qc
cd /opt/manar-qc
cp .env.example .env
# Edit .env to set SECRET_KEY, POSTGRES_PASSWORD, SIGNING_KEY_PATH, etc.
```

### Step 2: Generate Keypair & Seed Data
```bash
mkdir -p /secrets
docker compose run --rm web python manage.py genkeys /secrets
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py load_library
docker compose run --rm web python manage.py createsuperuser
```

### Step 3: Launch Service
```bash
docker compose up -d
```

---

## 2. Station Setup (Factory Offline Linux PC)

### Step 1: Install Dependencies
```bash
sudo apt-get update && sudo apt-get install -y python3-pip python3-venv openjdk-11-jre fonts-noto-ui-extra
python3 -m venv /opt/manar/.venv
source /opt/manar/.venv/bin/activate
pip install -r station/requirements-station.txt
```

### Step 2: Provision & Test
```bash
python -m station provision --cam 0 --sheet T-1100
python -m station import --pack /media/usb/manar_pack_XYZ_v1.mpk --pub /opt/manar/manar_sign.pub
```

### Step 3: Install Kiosk Systemd Service
```bash
sudo cp deploy/manar-station.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now manar-station.service
```

---

## 3. Maintenance & Troubleshooting

- **Station camera not detected:** Check `ls /dev/video*` and verify camera USB permissions (`sudo usermod -aG video $USER`).
- **Downgrade error on station import:** Station active pack version is higher than imported pack version. Increment version on portal.
- **Drift STOP triggered:** Cut loop stopped due to 5 consecutive panel measurements drifting beyond tolerance/2. Requires supervisor badge + PIN unlock.
