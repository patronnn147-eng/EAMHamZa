# model_loader.py

## What it does
Loads the trained AI model files (.pkl) from disk into memory, once, when first needed.

## Why it exists
Previously each model had a different loading style — some loaded at startup (crashing if a file was missing), one used a global variable. Now all 6 use the same safe pattern: load on first use, cache in memory, return None if the file is missing.

## Inputs / Outputs
- Input: nothing — reads from the path in `config.models_dir`
- Output: `load_p1()` through `load_p6()` — each returns the model object, or None if not found

## Who calls it
`predictions.py` calls `load_p1()` through `load_p6()` on every prediction request (the result is cached after the first call).

## What breaks if this file has a bug
Models may not load, causing all predictions to return safe defaults (0.0 / empty). The service stays up but gives no intelligence.

## Caching
Each `load_pN()` function uses `@lru_cache` — the pkl file is read from disk exactly once per service restart.
