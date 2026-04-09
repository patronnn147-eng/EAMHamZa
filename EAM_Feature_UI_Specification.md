# EAM System – UI & Implementation Specification

---

# 🔴 1. Downtime Tracking + MTTR / MTBF
**Impact: Very High**

## 🎯 Objective
Convert machine status changes into measurable production KPIs.

---

## 🖥️ UI DESIGN

### Machine Details Page

Add a new tab navigation:

[ Overview | Interventions | Maintenance | Reliability ]

---

## Reliability Tab Layout

### 1️⃣ KPI Cards (Top Section)

Display three statistic cards:

- **MTTR**
  - Large number (e.g. 4h 12m)
  - Small trend indicator (↑ or ↓ vs last month)

- **MTBF**
  - Large number
  - Trend comparison

- **Total Downtime (Last 30 Days)**
  - Duration format (e.g. 12h 43m)

All KPIs must be visible without scrolling.

---

### 2️⃣ Downtime Timeline Chart

- X-axis: Time
- Y-axis: Downtime duration
- Red markers: Breakdown events
- Filter: 30d / 90d / 1y

---

### 3️⃣ Downtime History Table

Columns:

| Date | Duration | Root Cause | Technician | Zone |

Rows clickable → open intervention details.

---

## ⚙️ Backend Logic

Trigger when:

IF old_status = EN_PANNE  
AND new_status = OPERATIONNEL  

THEN:

- downtime = now - panne_timestamp
- Save downtime record

Store:

- machine_id
- start_time
- end_time
- duration_minutes
- root_cause
- technician_id

### Calculations

MTTR = average(duration_minutes)  
MTBF = average(time_between_failures)

---

# 🔴 2. Machine Health Score
**Impact: High | Effort: Low**

## 🎯 Objective
Provide instant machine condition visibility.

---

## 🖥️ UI DESIGN

### Machine Card (List View)

Each machine card shows:

Machine Name  
Zone  
Status Badge  

Health Score: 78 / 100  
Progress bar with color gradient

Color Rules:

- 80–100 → Green
- 60–79 → Yellow
- <60 → Red (with alert icon)

---

### Machine Details Page – Health Panel

Right-side widget:

Machine Health Breakdown

- Days since last maintenance
- Open work orders
- Recent interventions (30 days)
- Current status

Final Score prominently displayed.

Include tooltip explaining score calculation.

---

## ⚙️ Scoring Formula

Start score = 100

Subtract:

- (days_since_last_maintenance × 0.5)
- (open_work_orders × 10)
- (recent_interventions × 8)

If status = EN_PANNE → subtract 30

Clamp result between 0 and 100.

---

# 🔴 3. QR Code per Machine
**Impact: High (Field Efficiency)**

## 🎯 Objective
Allow technicians instant mobile access to machine data.

---

## 🖥️ UI DESIGN

### Machine Detail Header

Buttons:

[ View QR ]  
[ Download QR ]

Click → Modal popup with:

- Large QR code centered
- Machine name below
- Caption: "Scan to access this machine instantly"

---

## 📱 Mobile View (After Scan)

Landing page shows:

Machine Name  
Status Badge  

Large Buttons:

- View History
- Create Intervention
- View Open Work Orders

Mobile-first design.

---

## ⚙️ Backend Implementation

QR content:

https://yourapp.com/machine/{machine_id}

- Generate once per machine
- Store PNG in media folder
- Regenerate only if missing

---

# 🟠 UI Consistency Rules

## Status Badges (System-wide)

- 🔴 EN_PANNE
- 🟡 EN_ATTENTE
- 🔵 EN_COURS
- 🟢 OPERATIONNEL

Must be visually consistent everywhere.

---

# 🟠 Zone Dashboard (Optional Enhancement)

Factory Overview Page:

Each Zone Card shows:

- Total Machines
- Status Distribution
- Average Health Score
- MTTR

Clickable → Zone Details Page

---

# 🚀 Implementation Order

1. Downtime logging backend
2. Reliability tab UI
3. Health score widget
4. QR code generation + mobile page

---

# Global UI Requirements

- KPIs visible without scrolling
- Use cards for summary data
- Charts support time filters (30d / 90d / 1y)
- All metrics filterable by machine and zone
- Mobile-friendly intervention creation
- Clean industrial design aesthetic

---

End of Specification