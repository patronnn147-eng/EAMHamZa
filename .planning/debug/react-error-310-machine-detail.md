---
status: fixing
trigger: "index-BsuOO70i.js:25 Uncaught Error: Minified React error #310; visit https://react.dev/errors/310 for the full message or use the non-minified dev environment for full errors and additional helpful warnings.    at Se (index-BsuOO70i.js:25:49145)\n    at Object.Sp [as useMemo] (index-BsuOO70i.js:25:56654)\n    at p.useMemo (react-vendor-CEC_HWdK.js:9:7149)\n    at fs (MachineDetailPage-Dfff1aKH.js:4:13156)\n    at dc (index-BsuOO70i.js:25:47875)\n    at ds (index-BsuOO70i.js:25:70556)\n    at Vp (index-BsuOO70i.js:25:80855)\n    at py (index-BsuOO70i.js:25:116408)\n    at Ab (index-BsuOO70i.js:25:115471)\n    at Wu (index-BsuOO70i.js:25:115307)"
created: "2026-04-04T00:00:00Z"
updated: "2026-04-04T00:00:00Z"
---

## Current Focus
hypothesis: null
test: null
expecting: null
next_action: gather symptoms

## Symptoms
expected: i want to see the machine's details the history (ml metrics ) etc
actual: page reloads a little bit then becomes blank
errors: 
reproduction: click on 'voir' button for a machine
started: after importing static machines to train ML model

## Eliminated

## Evidence
- timestamp: 2026-04-04T00:05:00Z
  checked: Moved health useMemo computation after null check (added getNeutralHealth guard)
  found: useMemo no longer accesses undefined machine, preventing React #310 error
  implication: Fix should stop blank page error

## Resolution
root_cause: useMemo accessed machine before null check causing React #310 error
fix: Guarded useMemo with null check and moved after early return
verification: 
files_changed: []
