# SagemCom Factory Floor Manual — Design Spec

**Date:** 2026-06-11
**Status:** Approved
**Format:** Single `.txt` file, bilingual (FR/EN), structured by machine category
**Purpose:** RAG corpus document — enables technicians to ask fault diagnosis, PM procedures, sensor threshold, and parts questions via chat

---

## Context

SagemCom Tunis manufacturing facility. 25 machines across two zones:
- **ZONE CMS1** — Component Surface Mounting (SMT production lines)
- **ZONE CMS2** — Test Zone (in-circuit, functional, WiFi/RF test benches)

Two production lines in CMS1:
- **Line 1 (BBS)** — Broadband products (modems, routers)
- **Line 2 (AVS)** — Audio/Video products

ML models P1–P7 monitor all machines using 5 telemetry sensors: `air_temperature`, `process_temperature`, `rotational_speed` (RPM), `torque`, `tool_wear`.

---

## Machine Inventory (all 25)

| ID | Machine Name (friendly) | Zone | Line |
|----|------------------------|------|------|
| 1  | Dépileur / Card Loader | CMS1 | BBS Line 1 |
| 2  | Sérigraphie DEK/MPM | CMS1 | BBS Line 1 |
| 3  | In-Circuit Test — Bed of Nails | CMS2 | Test |
| 4  | Functional Test Bench (Banc TF) | CMS2 | Test |
| 5  | Pick & Place Machine | CMS1 | BBS Line 1 |
| 6  | SPI (Solder Paste Inspection) | CMS1 | AVS Line 2 |
| 7  | AOI 3D — Final Inspection | CMS1 | BBS Line 1 |
| 8  | 2D Scanner — Component Inspection | CMS1 | BBS Line 1 |
| 9  | Reflow Oven (Four de Refusion) | CMS1 | BBS Line 1 |
| 10 | Dépileur AVS | CMS1 | AVS Line 2 |
| 11 | Sérigraphie AVS | CMS1 | AVS Line 2 |
| 12 | Pick & Place AVS | CMS1 | AVS Line 2 |
| 13 | 2D Scanner AVS | CMS1 | AVS Line 2 |
| 14 | AOI 3D AVS | CMS1 | AVS Line 2 |
| 15 | Reflow Oven AVS | CMS1 | AVS Line 2 |
| 16 | Manual Insertion Post AVS | CMS1 | AVS Line 2 |
| 17 | Wave Soldering AVS | CMS1 | AVS Line 2 |
| 18 | Front-End Test Bench (BFE) | CMS2 | Test |
| 19 | Audio/Video Test Bench (BAV) | CMS2 | Test |
| 20 | Router Test Bench | CMS2 | Test |
| 21 | WiFi Test PC | CMS2 | WiFi Test |
| 22 | Faraday Cage (Shielding Box) | CMS2 | WiFi Test |
| 23 | IQFlex RF Analyzer | CMS2 | WiFi Test |
| 24 | Wave Soldering BBS | CMS1 | BBS Line 1 |
| 25 | Manual THT Insertion Post BBS | CMS1 | BBS Line 1 |

---

## Document Structure

The manual is one `.txt` file (~2,000–3,000 lines). Each section uses clear bilingual headers so RAG chunking preserves machine context.

### Section 1: Factory Overview / Vue d'ensemble de l'usine
- Site description, production mission (broadband + AV electronics for SagemCom)
- Zone map description (CMS1 SMT flow left-to-right: load → print → place → inspect → solder → inspect; CMS2 test flow)
- Machine inventory table (all 25, ID, friendly name, zone, line)
- Roles: Technicien, ChefTech, ChefOp, Admin

### Section 2: Machine Categories — Specifications & Operating Parameters
One subsection per machine category (8 categories). Each subsection contains:
- **Function / Fonction** — what the machine does in the production flow
- **Key technical specs** — speed, capacity, temperature ranges, power
- **Which machines in DB** — by ID and friendly name
- **Normal sensor ranges** (all 5 telemetry sensors): air_temperature, process_temperature, rotational_speed (RPM), torque (Nm), tool_wear (hours/cycles)
- **Critical operating conditions** — what abnormal looks like

**8 machine categories:**
1. Dépileur / Card Loader (IDs 1, 10)
2. Sérigraphie / Stencil Printer (IDs 2, 6, 11)
3. Pick & Place / Machine de Pose (IDs 5, 12)
4. Inspection (2D Scanner + AOI 3D + SPI) (IDs 6, 7, 8, 13, 14)
5. Reflow Oven / Four de Refusion (IDs 9, 15)
6. Wave Soldering / Machine de Brassage à la Vague (IDs 17, 24)
7. Manual Insertion Post / Poste Insertion Manuelle (IDs 16, 25)
8. Test Benches / Bancs de Test (IDs 3, 4, 18, 19, 20, 21, 22, 23)

### Section 3: Preventive Maintenance Schedules / Plannings de Maintenance Préventive
Per machine category:
- **Daily (Quotidien)** — visual checks, cleaning, lubrication spot checks
- **Weekly (Hebdomadaire)** — filter cleaning, calibration check, sensor verification
- **Monthly (Mensuel)** — deep cleaning, belt/conveyor inspection, nozzle replacement
- **Annual (Annuel)** — full overhaul, bearing replacement, software backup

### Section 4: Fault Codes & Alarm Reference / Codes Défaut et Référence Alarmes
Mapped to ML failure types used in `ordres_intervention.actual_failure_type`:
- **TWF** — Tool Wear Failure: definition, triggering sensors, affected machines
- **HDF** — Heat Dissipation Failure: thermal causes, reflow oven + wave solder specific
- **PWF** — Power/Pressure Failure: electrical and pneumatic causes
- **OSF** — Overstrain Failure: mechanical overload, pick & place specific
- **RNF** — Random No Failure: no root cause identified

Per machine category: common alarm codes, meaning, immediate action.

### Section 5: Troubleshooting Guide / Guide de Dépannage
Symptom → Root Cause → Action tables per machine category.
Format per entry:
```
SYMPTOM / SYMPTÔME: [description]
PROBABLE CAUSE / CAUSE PROBABLE: [cause]
ACTION: [step-by-step resolution]
SENSORS TO CHECK / CAPTEURS À VÉRIFIER: [which of the 5 telemetry sensors]
PARTS POTENTIALLY NEEDED / PIÈCES POTENTIELLEMENT NÉCESSAIRES: [part refs]
```

Covers at minimum 4–5 symptom/cause/action entries per machine category.

### Section 6: Sensor Thresholds Reference Table / Tableau de Seuils des Capteurs
Master reference table — all 5 sensors × all 8 machine categories.

| Machine Category | Air Temp (°C) Normal | Process Temp (°C) Normal | RPM Normal | Torque (Nm) Normal | Tool Wear (h) Limit |
|-----------------|---------------------|-------------------------|------------|-------------------|---------------------|
| Dépileur | ... | ... | ... | ... | ... |
| Sérigraphie | ... | ... | ... | ... | ... |
| Pick & Place | ... | ... | ... | ... | ... |
| Inspection | ... | ... | ... | ... | ... |
| Reflow Oven | ... | ... | ... | ... | ... |
| Wave Soldering | ... | ... | ... | ... | ... |
| Manual Post | ... | ... | ... | ... | ... |
| Test Bench | ... | ... | ... | ... | ... |

Values derived from ai4i2020 dataset distributions (mean ± 2σ) calibrated to each machine type's operating profile.

### Section 7: Spare Parts Cross-Reference / Référence Croisée Pièces de Rechange
From `pieces` catalog + machine-type compatibility:
- Joint torique 10mm (REF-001): applicable machines and PM interval
- Roulement SKF 6205 / BEARING-A1 (TEST-001, REF-002): applicable machines
- OIL-B2 (REF-003): lubrication schedule per machine
- Grease A 250g (GREASE-A): applicable points per machine category
- Vises REF-005, Tournivuse REF-006: tools for maintenance

Per-machine spare parts list with replacement intervals.

### Section 8: Safety Procedures / Procédures de Sécurité
- **CMS1 SMT zone**: lead-free solder safety, high-temperature equipment (reflow 260°C peak), pneumatic systems lockout/tagout
- **CMS2 Test zone**: RF exposure (Faraday cage procedure), electrical test safety, ESD precautions
- General: PPE requirements, emergency stop locations, chemical handling (flux, solvents, paste)
- Lockout/Tagout procedure before maintenance

---

## Sensor Value Reference (basis for Section 6)

Based on ai4i2020 dataset used for ML training (type H = high-performance, similar to SMT equipment):

| Sensor | Dataset Mean | Dataset Std | Normal Range Used |
|--------|-------------|-------------|-------------------|
| Air Temperature | 300 K (27°C) | 2 K | 295–305 K |
| Process Temperature | 310 K (37°C) | 1.5 K | 307–313 K |
| Rotational Speed | 1500 RPM | 170 RPM | 1160–2660 RPM |
| Torque | 40 Nm | 10 Nm | 3.8–76.0 Nm |
| Tool Wear | 100–200 min | — | Warning >200 min, Critical >240 min |

Machine-type offsets applied:
- Reflow oven: process_temperature offset +200°C (actual oven zone ~220–260°C)
- Wave soldering: process_temperature offset +180°C
- Pick & place: lower torque range (precision servo, 3–15 Nm)
- Test benches: RPM = 0 (no rotating parts — N/A), torque N/A

---

## Output File

`docs/rag-corpus/sagemcom-factory-floor-manual.txt`

Approximate size: 2,000–3,500 lines of bilingual text.
Upload target: `POST /api/v1/rag/documents` with `doc_type=manual`.
