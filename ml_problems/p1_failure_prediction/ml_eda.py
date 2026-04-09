import pandas as pd
import numpy as np

# 1. Load the dataset
df = pd.read_csv('ai4i2020.csv')

print("--- Dataset Info ---")
print(df.info())

print("\n--- First 5 Rows ---")
print(df.head())

print("\n--- Missing Values ---")
print(df.isnull().sum())

print("\n--- Statistics for Numeric Columns ---")
# Focus on the telemetry columns
numeric_cols = [
    'Air temperature [K]', 
    'Process temperature [K]', 
    'Rotational speed [rpm]', 
    'Torque [Nm]', 
    'Tool wear [min]'
]
print(df[numeric_cols].describe())

print("\n--- Machine Failure Distribution ---")
print(df['Machine failure'].value_counts(normalize=True))

print("\n--- Correlation with Failure ---")
# Drop non-numeric IDs for correlation
correlation = df.drop(['UDI', 'Product ID', 'Type'], axis=1).corr()['Machine failure'].sort_values(ascending=False)
print(correlation)
