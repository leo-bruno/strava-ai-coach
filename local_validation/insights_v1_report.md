# Insights V1 — final offline validation

Validated: 7 October 2026. Status: COMPLETE for the three approved contracts.

Snapshot: `local_validation/strava_snapshot_2026-09-28.json`. No live requests, new data, production-code changes, or contract changes.

SHA-256 before and after: `69bb43aa007f7c010e8babc8dbdb1693cdab491bae79475e87acc1b8431038ac`.

## Pipeline and independent checks

Loaded the already-normalized Activity records from the snapshot, then rebuilt WeeklyAnalysis through weekly_analysis_from_activities for exactly the 24 dates supplied in snapshot.weeks. No dates were inferred or added. All three detectors used the same resulting history; Increase/Decrease used production Trends. HTTP requests were blocked during the offline audit.

Independently grouped the exported Run records by the ISO calendar week of their Europe/Madrid local start date, without production Analytics/history helpers. Counts and moving-time totals matched exactly, and production distances matched the snapshot totals exactly. Decimal source distance sums differed from float Analytics by at most 3.637978807091713e-12 m, within existing audit-only relative 1e-12/absolute 1e-9 tolerances. No tolerance, threshold or rounding was used in detection. Independent pattern enumeration used source totals/counts and explicit date lookup; results agreed with production.

89 activities, 59 Run, 468586.9 m source Run distance, 24 weekly observations from 2026-04-20 through 2026-09-28, 23 consecutive transitions and 21 possible four-week windows. Five observed zero-Run weeks. The final week was open at extraction; no calendar-closure filter was applied. This snapshot is not proof of complete real-world activity history.

## Exact weekly observations

| Local Monday | Distance (m), production float | Run count |
|---|---:|---:|
| 2026-04-20 | 22512.8 | 3 |
| 2026-04-27 | 10078.2 | 1 |
| 2026-05-04 | 23702.1 | 4 |
| 2026-05-11 | 21407.8 | 3 |
| 2026-05-18 | 17316.7 | 3 |
| 2026-05-25 | 25695.7 | 4 |
| 2026-06-01 | 0.0 | 0 |
| 2026-06-08 | 25888.300000000003 | 4 |
| 2026-06-15 | 28989.9 | 4 |
| 2026-06-22 | 10057.0 | 2 |
| 2026-06-29 | 31246.6 | 4 |
| 2026-07-06 | 35607.5 | 4 |
| 2026-07-13 | 36571.5 | 4 |
| 2026-07-20 | 26281.2 | 4 |
| 2026-07-27 | 41238.7 | 4 |
| 2026-08-03 | 21190.3 | 2 |
| 2026-08-10 | 19115.9 | 2 |
| 2026-08-17 | 0.0 | 0 |
| 2026-08-24 | 0.0 | 0 |
| 2026-08-31 | 0.0 | 0 |
| 2026-09-07 | 15495.9 | 2 |
| 2026-09-14 | 17096.0 | 2 |
| 2026-09-21 | 39094.8 | 3 |
| 2026-09-28 | 0.0 | 0 |

## Exact Insight results

PersistentWeeklyRunningDistanceIncrease: exactly ONE result.

Window: 2026-06-22 → 2026-06-29 → 2026-07-06 → 2026-07-13.

Distances (m): `(10057.0, 31246.6, 35607.5, 36571.5)`; Run counts: `(2, 4, 4, 4)`.

Changes (m): 2026-06-22 → 2026-06-29: `21189.6`; 2026-06-29 → 2026-07-06: `4360.9000000000015`; 2026-07-06 → 2026-07-13: `964.0`. Original Trends values and objects retained. The preceding 2026-06-15 observation is 28989.9 m / 4 Run; the following 2026-07-20 is 26281.2 m / 4 Run. Neither extends the strict increase.

PersistentWeeklyRunningDistanceDecrease: exactly ZERO results, `()`.

The strongest apparent candidate is 2026-07-27 → 2026-08-03 → 2026-08-10 → 2026-08-17: `(41238.7, 21190.3, 19115.9, 0.0)` m and `(4, 2, 2, 0)` Run. Its three negative transitions do not qualify because the fourth observation is ineligible. No other four-week source window satisfies the approved decrease contract.

ObservedRunningAfterZeroRunWeeks: exactly ONE result.

`first_zero_week_date = 2026-08-17`; `observed_zero_week_count = 3`; `running_week_date = 2026-09-07`; `running_week_activity_count = 2`; `running_week_distance_meters = 15495.9`.

The zero-Run observations are 2026-08-17, 2026-08-24 and 2026-08-31, all count 0 / distance 0.0. The preceding 2026-08-10 has 2 Run / 19115.9 m; the following 2026-09-14 has 2 Run / 17096.0 m. The complete supplied episode produces one result, not overlapping two-zero-week subwindows.

## False-positive and false-negative review

No false positives or false negatives were found in the 21 source four-week windows and the independently enumerated zero-Run sequences. Equal-distance transitions 2026-08-17 → 2026-08-24 and 2026-08-24 → 2026-08-31 produce no distance Insight. Zero-Run observations are excluded from eligible Increase/Decrease windows.

The isolated zero-Run week 2026-06-01 followed by 2026-06-08 produces no episode Insight. The trailing 2026-09-28 zero observation has no following running observation and produces none. The sole qualifying zero episode is maximal. This snapshot has no multiple qualifying episodes; their separation is covered by the passing existing unit tests, rather than claimed as additional real-data evidence.

Normal, reversed and deterministic permuted histories produced the same exact results. Each of the 24 supplied weeks was also removed separately in memory, without editing the source. Every derived-history result matched the independent date-based oracle. Gaps were never bridged or filled with zeros.

Removing any Increase member eliminates Increase. Removing 2026-08-24 or 2026-08-31 eliminates the observed-running Insight; removing 2026-09-07 prevents connecting the zero sequence to 2026-09-14. Removing 2026-08-17 correctly leaves a new two-zero-week episode starting 2026-08-24.

## Mutation and integration

All three detectors ran together and repeatedly in all 27 cases. History values/order, observation identities, TrainingType tuple/member identities and values remained unchanged. Activity values/order remained unchanged. Captured real Trends objects were shared with both distance detectors; Increase preserved the original objects and no Trends values or identities changed. Decrease produces no real-snapshot result; its evidence identity remains covered by the existing automated tests. Snapshot SHA-256 remained unchanged.

## Derived-history checks

| Case | Increase | Decrease | Observed running |
|---|---:|---:|---:|
| normal | 1 | 0 | 1 |
| reverse | 1 | 0 | 1 |
| permutation | 1 | 0 | 1 |
| remove_2026-04-20 | 1 | 0 | 1 |
| remove_2026-04-27 | 1 | 0 | 1 |
| remove_2026-05-04 | 1 | 0 | 1 |
| remove_2026-05-11 | 1 | 0 | 1 |
| remove_2026-05-18 | 1 | 0 | 1 |
| remove_2026-05-25 | 1 | 0 | 1 |
| remove_2026-06-01 | 1 | 0 | 1 |
| remove_2026-06-08 | 1 | 0 | 1 |
| remove_2026-06-15 | 1 | 0 | 1 |
| remove_2026-06-22 | 0 | 0 | 1 |
| remove_2026-06-29 | 0 | 0 | 1 |
| remove_2026-07-06 | 0 | 0 | 1 |
| remove_2026-07-13 | 0 | 0 | 1 |
| remove_2026-07-20 | 1 | 0 | 1 |
| remove_2026-07-27 | 1 | 0 | 1 |
| remove_2026-08-03 | 1 | 0 | 1 |
| remove_2026-08-10 | 1 | 0 | 1 |
| remove_2026-08-17 | 1 | 0 | 1 |
| remove_2026-08-24 | 1 | 0 | 0 |
| remove_2026-08-31 | 1 | 0 | 0 |
| remove_2026-09-07 | 1 | 0 | 0 |
| remove_2026-09-14 | 1 | 0 | 1 |
| remove_2026-09-21 | 1 | 0 | 1 |
| remove_2026-09-28 | 1 | 0 | 1 |

## Automated regression and closure

After the offline audit, the complete configured suite passed: **846 tests**, including the mocked integration test. Coverage: **97.79086892488954% combined** (664/679), **98.37251356238698% statements** (544/553), **95.23809523809524% branches** (120/126). Both Insight detector modules and all three Insight models have 100% statement/branch coverage. No production functionality or contracts changed, and no unresolved defect was found.

Insights V1 is COMPLETE with PersistentWeeklyRunningDistanceIncrease, PersistentWeeklyRunningDistanceDecrease and ObservedRunningAfterZeroRunWeeks. This closes the supplied-observation detection foundation; it does not certify calendar closure, coverage or completeness, and does not establish physiology, actual inactivity/rest or recommendations. AI Coach V1 design is next; no Coach implementation was started.
