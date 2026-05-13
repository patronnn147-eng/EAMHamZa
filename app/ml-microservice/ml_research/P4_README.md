# P4 — Anomaly Detection

---

## Imagine this

A machine on your floor is behaving strangely. Nothing has broken yet. No alarm has triggered. But something is off — temperatures are slightly higher than usual, vibration patterns have shifted. A seasoned technician would notice. But you can't have a seasoned technician watching every machine every minute.

This model watches instead. It learned what "normal" looks like for every machine, and it raises a flag the moment something stops looking normal — **before anything breaks**.

---

## The business problem it solves

Traditional monitoring waits for a threshold to be crossed: "alert if temperature exceeds 400K." But machines don't always fail in obvious ways. They degrade gradually, in combinations of small signals that no single threshold catches.

Without this model:
- You only know something is wrong after it breaks
- Rule-based alerts miss subtle multi-sensor patterns
- New failure types (ones you've never seen before) go completely undetected

With this model:
- Unusual behavior is flagged automatically, even if no individual sensor is in the red
- Catches failure patterns that have never happened before — because it learned "normal", not "known failures"
- Works as a first filter: flag the suspicious machines, send a technician to investigate

---

## What the model actually does

Four independent detection methods each analyze the sensor data and vote on whether a machine is behaving abnormally. Their votes are combined into a single score — the higher the score, the more suspicious the machine.

**The four detectors:**

**1. Autoencoder (40% of the vote)**
This is a neural network trained only on healthy machines. It learned to "reconstruct" what normal sensor readings look like. When you show it a broken machine's readings, it can't reconstruct them well — the reconstruction error is high. High error = anomaly.
*Analogy: a native English speaker instantly notices a sentence that sounds wrong, even if they can't explain the grammar rule.*

**2. Isolation Forest (30% of the vote)**
Groups all machine readings into a forest of decision trees. Readings that get "isolated" quickly — far from the main cluster — are flagged as anomalies.
*Analogy: at a party, the person standing alone in the corner is easier to isolate than someone in the middle of the crowd.*

**3. Z-Score (20% of the vote)**
Flags any sensor reading that is statistically far from the average. Simple but fast — catches obvious outliers.
*Analogy: if everyone in the office is paid between 30K–80K and someone earns 500K, that's a statistical outlier.*

**4. Cluster Deviation (10% of the vote)**
Machines normally operate in one of 3 "states" (e.g., low load, high load, transition). A machine far from all 3 states is suspicious.
*Analogy: a car should either be parked, cruising, or accelerating. If it's doing none of those, something is wrong.*

---

## How to read the results

**Detection accuracy (ROC-AUC)**
This number answers: "Out of 100 random pairs — one healthy machine, one broken — how often does the model correctly identify which is which?"

| Score | What it means |
|-------|--------------|
| 0.50 | Coin flip — completely useless |
| 0.70 | Decent — catches most obvious cases |
| **0.83** | **Good — our current baseline (Isolation Forest alone)** |
| 0.90+ | Excellent |

The ensemble (all 4 detectors combined) beats the single Isolation Forest. That's why we use it.

---

## The traffic light

| | Detection Accuracy (ROC-AUC) |
|---|---|
| 🟢 Good | > 0.83 (beats baseline) |
| 🟡 Acceptable | 0.75–0.83 |
| 🔴 Poor | < 0.75 |

*Current ensemble: ROC-AUC = beats baseline 🟢 → graduated to production*

---

## What "graduated" means for operations

**When the ensemble graduates:**
The combined 4-detector model is more accurate than using Isolation Forest alone. It replaces the simpler model in production. The anomaly scores shown in the maintenance dashboard now reflect this richer detection — expect slightly different rankings of "suspicious" machines.

**When the ensemble does NOT graduate:**
The 4-detector combination didn't beat the simpler model. The existing Isolation Forest stays in production. Operations sees no change. Engineering investigates why the ensemble underperformed.

**What changes in the system:**
The "anomaly score" attached to each machine in the dashboard is recalculated. A machine that scored 0.4 before might score 0.7 now — meaning the new model sees it as more suspicious. Technicians should re-review machines flagged by the new model that weren't flagged before.

---

## FAQ

**Q: Can it tell me *why* a machine is flagged?**
Not directly — it flags "something is off" without naming the exact cause. Think of it as a first responder: it identifies *that* there's a problem, then a technician investigates *what* the problem is.

**Q: What if it flags a healthy machine (false alarm)?**
It will happen occasionally. The model is tuned for the failure rate in our dataset (~3.4% of readings are from failing machines). False alarms are a tradeoff against missed detections — we'd rather investigate a false alarm than miss a real failure.

**Q: What if it misses a real failure?**
No model is perfect. This works best as one layer of a maintenance strategy, not the only one. Combine with P3 (RUL prediction) and regular technician rounds for best coverage.

**Q: Does it need to know what failure looks like to detect it?**
No — and this is its biggest advantage. It only learns what *healthy* looks like. This means it can catch brand-new failure types it has never seen before, because anything that looks "not normal" gets flagged.

**Q: How is this different from a simple temperature alarm?**
A temperature alarm fires when one sensor crosses a threshold. This model looks at all 5 sensors simultaneously and their combinations. A machine can have normal temperature but abnormal torque-to-speed ratio — that pattern would be invisible to simple alarms but visible here.
