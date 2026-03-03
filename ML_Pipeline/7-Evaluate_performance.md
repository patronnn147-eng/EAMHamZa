# ML Pipeline — EAMSagemCom
## Step 7: Evaluate Performance

Each problem uses the evaluation metrics best suited to its type. This step runs on the **untouched test set** — data the model has never seen during training or tuning.

---

## Problem 1 — Binary Failure Prediction

### Why NOT accuracy?

A model that always predicts "Healthy" gets **96.6% accuracy** — but catches **zero failures**. Therefore we use:

- **Precision** — Of all predicted failures, how many were real?
- **Recall** — Of all real failures, how many did we catch? *(most important)*
- **F1-Score** — Harmonic mean of Precision & Recall
- **Confusion Matrix** — Full breakdown of TP, FP, FN, TN

```python
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt

y_pred_p1 = best_model_p1.predict(X_test)

# Full report
print(classification_report(y_test, y_pred_p1, target_names=["Healthy", "Failure"]))

# Confusion matrix plot
cm = confusion_matrix(y_test, y_pred_p1)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Healthy", "Failure"])
disp.plot(cmap='Blues')
plt.title("P1 — Failure Prediction: Confusion Matrix")
plt.savefig("ML_Pipeline/outputs/p1_confusion_matrix.png")
plt.show()
```

**Expected output:**
```
              precision  recall  f1-score  support
Healthy           0.99    0.97      0.98     1933
Failure           0.72    0.88      0.79       67  ← Recall is key
accuracy                            0.97     2000
```

**Key targets:**
| Metric | Target |
|---|---|
| Recall (Failure) | > 80% — don't miss real failures |
| Precision (Failure) | > 65% — avoid too many false alarms |
| F1-Score | > 75% |

---

## Problem 2 — Failure Type Classification (Multi-label)

```python
from sklearn.metrics import classification_report

y_pred_p2 = model_p2.predict(X_test_p2)

labels = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
for i, label in enumerate(labels):
    print(f"\n--- {label} ---")
    print(classification_report(y_test_p2.iloc[:, i], y_pred_p2[:, i],
                                 target_names=["No", "Yes"]))
```

**Key insight from dataset analysis:**
- `HDF` (Heat Dissipation) has the strongest correlation with failure → highest recall expected
- `RNF` (Random Failure) is nearly impossible to predict → lowest performance expected

---

## Problem 3 — RUL Estimation (Regression)

```python
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import numpy as np

y_pred_p3 = model_p3.predict(X_test_r)

rmse = np.sqrt(mean_squared_error(y_test_r, y_pred_p3))
mae  = mean_absolute_error(y_test_r, y_pred_p3)
r2   = r2_score(y_test_r, y_pred_p3)

print(f"RMSE : {rmse:.2f} days")  # Average error in days
print(f"MAE  : {mae:.2f} days")   # Mean absolute error
print(f"R²   : {r2:.4f}")         # 1.0 = perfect, 0 = no better than mean

# Plot predicted vs actual
plt.scatter(y_test_r, y_pred_p3, alpha=0.4)
plt.plot([0, max(y_test_r)], [0, max(y_test_r)], 'r--', label='Perfect prediction')
plt.xlabel("Actual RUL (days)")
plt.ylabel("Predicted RUL (days)")
plt.title("P3 — RUL: Predicted vs Actual")
plt.savefig("ML_Pipeline/outputs/p3_rul_scatter.png")
plt.show()
```

| Metric | Meaning | Target |
|---|---|---|
| RMSE | Penalises large errors heavily | < 10 days |
| MAE | Average absolute error in days | < 7 days |
| R² | Proportion of variance explained | > 0.85 |

---

## Problem 4 — Anomaly Detection (Isolation Forest)

Since this is unsupervised, we **do** have labels in `ai4i2020.csv` — we use them only for evaluation, not training.

```python
from sklearn.metrics import classification_report

# Model outputs: -1 (anomaly) or +1 (normal)
# Convert to 0/1 to match y_test labels
y_pred_ad = model_p4.predict(X_score_ad)
y_pred_ad_binary = (y_pred_ad == -1).astype(int)  # -1 → 1 (anomaly), +1 → 0 (normal)

y_true_ad = df_p4['Machine failure'].values

print(classification_report(y_true_ad, y_pred_ad_binary, target_names=["Normal", "Anomaly"]))
```

> ⚠️ Unsupervised models typically have lower recall than supervised ones — they don't use labels during training. The goal is catching **obvious deviations**, not all edge cases.

---

## Problem 5 — Work Order Priority (Multi-class)

```python
from sklearn.metrics import classification_report, confusion_matrix, ConfusionMatrixDisplay

y_pred_p5 = model_p5.predict(X_test_wo)
labels = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

print(classification_report(y_test_wo, y_pred_p5, target_names=labels))

cm = confusion_matrix(y_test_wo, y_pred_p5)
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=labels)
disp.plot(cmap='Oranges')
plt.title("P5 — Work Order Priority: Confusion Matrix")
plt.savefig("ML_Pipeline/outputs/p5_priority_confusion.png")
plt.show()
```

Use **macro F1** — treats all 4 priority classes equally:

```python
from sklearn.metrics import f1_score
macro_f1 = f1_score(y_test_wo, y_pred_p5, average='macro')
print(f"Macro F1: {macro_f1:.4f}")
```

---

## Problem 6 — Maintenance Scheduling (Prophet)

```python
# Forecast future maintenance windows
future = model_p6.make_future_dataframe(periods=90)  # 90 days ahead
forecast = model_p6.predict(future)

# Plot forecast
fig = model_p6.plot(forecast)
plt.title("P6 — Maintenance Schedule Forecast")
plt.savefig("ML_Pipeline/outputs/p6_forecast.png")
plt.show()

# Evaluate on test period
from sklearn.metrics import mean_absolute_error
y_pred_ts = forecast.set_index('ds').loc[df_test_ts['date'], 'yhat'].values
mae_ts = mean_absolute_error(df_test_ts['days_between'], y_pred_ts)
print(f"MAE: {mae_ts:.2f} days")
```

---

## Feature Importance (P1 & P2)

Always check which features drive predictions — crucial for the tutor presentation:

```python
import pandas as pd
import matplotlib.pyplot as plt

importances = best_model_p1.feature_importances_
feat_names  = ['Air Temp', 'Process Temp', 'RPM', 'Torque', 'Tool Wear']

fi_df = pd.DataFrame({'Feature': feat_names, 'Importance': importances})
fi_df = fi_df.sort_values('Importance', ascending=True)

fi_df.plot.barh(x='Feature', y='Importance', color='steelblue', legend=False)
plt.title("P1 — Feature Importance (XGBoost)")
plt.tight_layout()
plt.savefig("ML_Pipeline/outputs/p1_feature_importance.png")
plt.show()
```

**Expected ranking** (from EDA in AGENT.md):
1. 🥇 Tool Wear — highest importance
2. 🥈 Torque
3. 🥉 Heat / Process Temperature (HDF driver)

---

## Evaluation Summary

| Problem | Primary Metric | Secondary Metric | Target |
|---|---|---|---|
| P1 — Failure Prediction | Recall (Failure) | F1-Score | Recall > 80% |
| P2 — Failure Type | F1 per label | Recall per label | HDF recall > 75% |
| P3 — RUL Estimation | RMSE (days) | R² | RMSE < 10 days |
| P4 — Anomaly Detection | Recall (Anomaly) | Precision | Catch obvious deviations |
| P5 — Work Order Priority | Macro F1 | Confusion Matrix | Macro F1 > 70% |
| P6 — Scheduling | MAE (days) | Visual forecast plot | MAE < 5 days |
