# Stage 4 — Historical Validation Report

The engine optimizes **free-air race time**: it ignores track position, traffic and the undercut. It is therefore *expected* to disagree with what teams actually did — and those disagreements, explained below, are the point of this stage. Validation runs over the cached races the engine can generate for; Australia is excluded (only one compound survives the data gate).

## At a glance

| Race | Stop Count | Pit MAE | Compound | Timing Err | Explanation |
|------|:----------:|:-------:|:--------:|:----------:|-------------|
| Bahrain | ✅ | 1.0 laps | ~ | +45.3 s | Same compounds, reordered |
| Spanish | ✅ | 9.0 laps | ❌ | +22.1 s | Team ran long (overcut) |
| Austrian | ✅ | 5.5 laps | ~ | +86.2 s | Team ran long (overcut) |
| Singapore | ❌ | N/A | ❌ | -0.3 s | Compound mismatch |
| Japanese | ✅ | 2.0 laps | ❌ | +16.1 s | Early undercut |

_Compound: ✅ exact sequence · ~ same compounds reordered · ❌ different compounds_

**Aggregate** — pit-lap MAE (stop-count matches): **4.38 laps** · first-stop MAE: **4.2 laps** · stop-count mismatches: **1/5** · exact compound matches: **0/5** · mean abs timing error: **34.01 s**

## Timing-model axis (independent of strategy choice)

Predicted total vs a free-air reconstruction of the winner's time (`median green lap × laps + stops × pit-loss`). Both sides are free-air, so this isolates the pace/degradation model from the strategy recommendation.

| Race | Predicted (s) | Actual est. (s) | Error (s) | Lap coverage |
|------|--------------:|----------------:|----------:|:------------:|
| Bahrain | 5651.2 | 5605.9 | +45.3 | 88% |
| Spanish | 5285.0 | 5262.9 | +22.1 | 92% |
| Austrian | 5057.2 | 4971.0 | +86.2 | 83% |
| Singapore | 6200.7 | 6201.0 | -0.3 | 90% |
| Japanese | 5231.7 | 5215.6 | +16.1 | 83% |

## Largest disagreements

### Spanish — first-stop error 8 laps

- **Engine (deterministic top-1):** `M-S-S@18,42` (M-S-S), stops at 18/42
- **Actual winner (VER):** M-H-S, stops at 26/52
- **Robust pick (Stage 3):** `S-M-S@24,43`  _(differs from deterministic headline)_
- **Field median first stop:** lap 16
- **Timing axis:** predicted 5285.0s vs actual est. 5262.9s (+22.1s)

_Candidate explanation: **Team ran long (overcut).**_ The engine optimizes free-air pace and does not model track position, traffic or the undercut — so an earlier real stop is expected where those forces dominate. <!-- Add hand-written analysis here. -->

### Austrian — first-stop error 6 laps

- **Engine (deterministic top-1):** `H-M-M@18,44` (H-M-M), stops at 18/44
- **Actual winner (VER):** M-H-M, stops at 24/49
- **Robust pick (Stage 3):** `H-M-M@17,44`  _(differs from deterministic headline)_
- **Field median first stop:** lap 14
- **Timing axis:** predicted 5057.2s vs actual est. 4971.0s (+86.2s)

_Candidate explanation: **Team ran long (overcut).**_ The engine optimizes free-air pace and does not model track position, traffic or the undercut — so an earlier real stop is expected where those forces dominate. <!-- Add hand-written analysis here. -->

### Japanese — first-stop error 3 laps

- **Engine (deterministic top-1):** `M-S-S@19,36` (M-S-S), stops at 19/36
- **Actual winner (VER):** M-M-H, stops at 16/37
- **Robust pick (Stage 3):** `M-S-S@19,36`
- **Field median first stop:** lap 14
- **Timing axis:** predicted 5231.7s vs actual est. 5215.6s (+16.1s)
- **Data-driven flags:**
  - undercut-signature: actual first stop 3 laps earlier than predicted with no SC coincidence (free-air model ignores track position)

_Candidate explanation: **Early undercut.**_ The engine optimizes free-air pace and does not model track position, traffic or the undercut — so an earlier real stop is expected where those forces dominate. <!-- Add hand-written analysis here. -->
