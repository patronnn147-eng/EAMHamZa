# feature_pipeline.py

## What it does
Takes raw sensor readings and turns them into the number arrays the AI models expect.

## Why it exists
Before this file, every prediction method computed the same two numbers (temperature difference, RPM×Torque) independently. That meant the same formula existed 6 times and could drift. Now it's one place.

## Inputs / Outputs
- Input: a `SensorReading` (air temp, process temp, RPM, torque, tool wear)
- Output: a list of numbers — either 5 (raw only) or 7 (raw + 2 derived values)

## Who calls it
`predictions.py` and `router.py` — everywhere a model needs to be called.

## Derived features
| Feature | Formula | Used by |
|---------|---------|---------|
| `temp_delta` | process_temp − air_temp | P1, P2, P5, P6 |
| `rpm_torque` | (RPM × torque) ÷ 1000 | P1, P2, P5, P6 |

## What breaks if this file has a bug
All model predictions receive wrong numbers. A formula error here affects all 6 models simultaneously.
