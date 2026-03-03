import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import joblib
from imblearn.over_sampling import SMOTE

# 1. Load data
df = pd.read_csv('ai4i2020.csv')

# 2. Basic Preprocessing
# We use the telemetry columns as features (X)
# And 'Machine failure' as the target (y)
features = [
    'Air temperature [K]',
    'Process temperature [K]',
    'Rotational speed [rpm]',
    'Torque [Nm]',
    'Tool wear [min]'
]
X = df[features]
y = df['Machine failure']

# 3. Split data (80% train, 20% test)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

print(f"Training set size: {len(X_train)}")
print(f"Testing set size: {len(X_test)}")

# 4. Oversample minority class using SMOTE
smote = SMOTE(random_state=42)
X_res, y_res = smote.fit_resample(X_train, y_train)

# 5. Hyper‑parameter tuning with GridSearchCV
param_grid = {
    'n_estimators': [200, 300],
    'max_depth': [None, 10, 20],
    'min_samples_split': [2, 5]
}
grid = GridSearchCV(
    estimator=RandomForestClassifier(class_weight='balanced', random_state=42),
    param_grid=param_grid,
    cv=3,
    scoring='f1',
    n_jobs=-1
)
grid.fit(X_res, y_res)

best_model = grid.best_estimator_
print("\nBest hyper-parameters:")
print(grid.best_params_)

# 6. Evaluate on held-out test set
y_pred = best_model.predict(X_test)
print("\n--- Confusion Matrix ---")
print(confusion_matrix(y_test, y_pred))
print("\n--- Classification Report ---")
print(classification_report(y_test, y_pred))

# 7. Save the best model
model_filename = 'basic_machine_model.pkl'
joblib.dump(best_model, model_filename)
print(f"\nModel saved to {model_filename}")

# 8. Quick Test with a manual input
sample_input = np.array([[300.0, 310.0, 1500, 40.0, 5]])
prediction = best_model.predict(sample_input)
probability = best_model.predict_proba(sample_input)

print("\n--- Manual Test ---")
print(f"Input: {sample_input}")
print(f"Prediction: {'FAILURE' if prediction[0] == 1 else 'HEALTHY'}")
print(f"Probability: {probability[0]}")
