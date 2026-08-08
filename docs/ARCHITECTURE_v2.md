# MANAR QC — Dimensional Control System  
## Product & Technical Architecture · v2.0 (supersedes v1.0 concept, Aug 2026)  
**Company:** Manar (manar.pk) · Sovereign systems, Pakistan  
**Status:** Design validated · sheets certified · full stack coded · assembly/deployment in progress

---

## 1 · Executive Summary

Manar QC is an offline, portable, calibrated **2D dimensional-control instrument** for Pakistan's export textile sector. A garment (or cut panel) is laid on a printed calibration sheet; an overhead camera measures it against the buyer's spec; the screen shows an unambiguous **ٹھیک ہے / فیل** verdict in ~2 s with a photographic, hash-chained, timestamped audit trail stored on-device.

Core claims:  
- **Millimeter-level accuracy** vs AQL ±5–10 mm tolerances, via calibrated geometry — **no AI training, ever**.  
- **Fully offline stations.** Nothing leaves the factory by default; opt-in aggregates only.  
- **Portable instrument, not a fixed machine:** sheet + camera + PC on any flat surface; no special table.  
- **Two checkpoints:** CUT (cutting table, catches systematic errors before value is added) and FINAL (finishing end, buyer measurement points).  
- **Compliance-grade records:** tester-stamped (name + code), per-garment photo + overlay + values + pack/spec version; exportable PDF/CSV for buyer QA audits.  
- **Cloud portal (qcg.manar.pk)** for vendors: buyers (ZARA/H&M) → categories → styles/SKUs → CUT/FIN spec matrices → signed station packs; enterprise SSO + self-hosted edition.

---

## 2 · System Overview

```  
            PORTAL qcg.manar.pk (Django5+Postgres, Traefik, TLS)  
   vendors→units→stations · buyers→categories→styles→SpecSets(CUT|FIN)  
   workorders→lays→bundles(ticket QR) · signed packs · audit · verify  
            │ signed packs down (USB)        ▲ opt-in aggregates up  
   ┌────────┴────────────────────────────────┴───────────────────────┐  
   │ STATION (offline Linux PC, systemd kiosk)                       │  
   │ shift(tester badge+PIN) → CUT / FINAL loop → verdict+tones+Urdu │  
   │ camera+sheet pipeline · refuse-don't-guess · drift STOP         │  
   │ SQLite hash-chained records+photos · PDF · USB export           │  
   └─────────────────────────────────────────────────────────────────┘  
            ▲ garment / cut panel laid on certified sheet v3  
```

---

## 3 · Certified Calibration Sheets

| Sheet ID | Outer (mm) | Markers | Main Application |
|---|---|---|---|
| T-1100 | 1100×900 | 8 ArUco (DICT_5X5_100) | Tees, polos, shirts |
| U-1400 | 1400×900 | 10 ArUco | Sweats, hoodies, jackets, trousers |
| SHOE-600 | 600×450 | 8 ArUco (30mm) | Shoe vamps, quarters, insoles |
