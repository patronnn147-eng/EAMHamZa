# feature_validator.py

## What it does
Checks that sensor readings from the frontend are within physically plausible ranges before the AI models see them.

## Why it exists
A sensor malfunction or data entry error could send -999 RPM or 50,000°C. Without validation, the models produce nonsense outputs. This file catches bad data at the entry point.

## Inputs / Outputs
- Input: a dict of sensor readings from the API request
- Output: raises `ValueError` if any field is out of range; silent if all good

## Who calls it
API routes in `router.py` can call `FeatureValidator.validate()` before passing data to predictions.

## Validation ranges
| Sensor | Min | Max |
|--------|-----|-----|
| Air temperature | 0 | 2,000 |
| Process temperature | 0 | 5,000 |
| Rotational speed (RPM) | 0 | 10,000 |
| Torque (Nm) | 0 | 1,000 |
| Tool wear (min) | 0 | 300 |

## What breaks if this file has a bug
Invalid sensor data reaches the models. Predictions may be nonsensical. In the worst case, a very large or very negative value causes a model to crash or return NaN.
