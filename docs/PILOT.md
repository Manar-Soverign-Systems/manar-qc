# MANAR QC — Validation Protocol & Pilot Week Runbook (§13 Gate)

## Pilot Validation Protocol

Before any factory deployment is accepted by EU/US buyer QA, the station instrument must undergo a 5-day on-site validation protocol.

### §13 Gate Criteria
1. **Sample Size:** 30–50 pieces per garment category measured in parallel by station system and manual tape checker.
2. **MAE Gate:** Mean Absolute Error (MAE) $\le \max(2.0\text{ mm}, \text{tolerance}/3)$.
3. **Tolerance Gate:** $\ge 95\%$ of system measurements within buyer tolerance band.
4. **False-OK Gate:** 0 false-OK verdicts (system reported PASS when manual tape measured out-of-spec).
5. **False-FAIL Gate:** $<5\%$ false-FAIL verdicts (system reported FAIL when manual tape measured in-spec).

---

## Execution Steps

### 1. Provision Station
```bash
python -m station provision --cam 0 --sheet T-1100
```
Verify `provision_report.json` outputs `"camera": true`, `"light_ok": true`, `"sheet_ok": true`, `"pack_ok": true`.

### 2. Collect Validation Measurements
1. Station measures 30–50 garments in `final` mode.
2. Checker tapes the same garments in identical order and records values into `tape.csv`.
3. Station exports batch records to `records.csv`.

### 3. Generate Agreement Report
```bash
python -m station validate --records records.csv --tape tape.csv --pack pack.json --out validation_report
```

### 4. Review & Sign Report
- Output generated: `validation_report.csv` and `validation_report.pdf`.
- If all gates print `GATE PASS`, the signed validation PDF becomes the formal sales and compliance artifact.
