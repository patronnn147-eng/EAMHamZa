# P3 — Remaining Useful Life Prediction

---

## Imagine this

You manage a factory floor with dozens of machines running 24/7. Each one will eventually break down — the question is *when*. Right now, you either wait for it to break (expensive emergency repair, production stop) or replace parts on a fixed calendar schedule (wasteful — you're often replacing things that still have months of life left).

This model changes that. It watches the sensor data from each machine and answers one question: **"How many production cycles does this machine have left before it needs attention?"**

---

## The business problem it solves

Without this model:
- Maintenance is reactive (machine breaks → panic → cost)
- Or maintenance is calendar-based (replace every 3 months → waste)
- You have no way to prioritize: *which* machine needs attention *first*?

With this model:
- You get a predicted remaining life for every machine
- You can rank machines by urgency: Machine A has 8 cycles left, Machine B has 45 — fix A first
- You schedule maintenance windows based on actual need, not guesswork

---

## What the model actually does

The model reads 5 sensor values from each machine — temperature, speed, torque, tool wear, and pressure. But instead of just looking at the current reading (like a snapshot), it watches the **last 20 cycles** of history and learns *how the machine has been changing over time*. A machine that's been slowly getting hotter for 10 cycles is more at risk than one that spiked once.

Think of it like a doctor who reads your last 20 blood test results instead of just today's — they can see a trend you can't.

---

## How to read the results

When the notebook finishes, you'll see three numbers for each model. Here's what they actually mean:

**Prediction error (MAE) — currently 14.95 cycles**
On average, the model's prediction is off by about 15 cycles. If it says a machine has 50 cycles left, the real answer is somewhere between 35 and 65. Think of it like a weather forecast — it won't be exact, but it's directionally correct and far better than nothing.
→ Lower is better. The previous model was off by 16.25 cycles. This one improved that.

**Ranking accuracy (C-index) — currently 62%**
Out of every 100 random pairs of machines, the model correctly identifies which one will break first 62 times. The previous model was right only 59 times out of 100.
→ 50% = coin flip (useless). 62% = meaningfully better than chance. For scheduling, this is the number that matters most — you need to know *who breaks first*, not the exact date.

**Fit score (R²) — currently near 0**
How well the model predicts exact cycle counts. This is intentionally not the priority — for maintenance scheduling, ranking machines correctly matters more than hitting exact numbers.

---

## The traffic light

| | Prediction Error (MAE) | Ranking Accuracy (C-index) |
|---|---|---|
| 🟢 Good | < 15 cycles | > 62% |
| 🟡 Acceptable | 15–20 cycles | 58–62% |
| 🔴 Poor | > 20 cycles | < 58% |

*Current model: MAE = 14.95 🟢 · C-index = 62% 🟢*

---

## What "graduated" means for operations

**When a model graduates:**
The new model passed both tests — it ranks machines more accurately than the previous version AND its prediction error is within acceptable range. The system automatically replaces the old model with the new one. No action needed from operations.

**When a model does NOT graduate:**
The new model wasn't good enough. The existing production model stays in place — nothing changes for operations. The data science team will investigate and retrain.

**What changes in the system when a new model graduates:**
The predictions shown in the maintenance dashboard will update. Machines that were previously ranked 3rd urgency might move to 1st. This is normal — the new model has learned something the old one hadn't.

---

## FAQ

**Q: Does it work on all machine types?**
Currently trained on data from our AI4I dataset representing 100 machines across various operating conditions. It generalizes well within the same sensor profile. If a new type of machine with different sensors is added, the model would need retraining on that data.

**Q: What if the prediction is wrong?**
The model gives a range, not a guarantee. A prediction of "50 cycles remaining" means "probably between 35 and 65." Use it to prioritize — don't use it as a hard deadline. Always combine with technician judgment.

**Q: How often does it retrain?**
Retraining is triggered manually or on a schedule by the engineering team. Each retraining run produces a new candidate model that goes through the same graduation test before replacing the current one.

**Q: Why 20 cycles of history?**
Testing showed that looking at 20 cycles back captures meaningful degradation trends without being too noisy. Fewer cycles = missed patterns. More cycles = too slow to react to sudden changes.

**Q: What sensors does it use?**
Air temperature, process temperature, rotational speed, torque, and tool wear. These are the five core indicators of mechanical stress and degradation.
