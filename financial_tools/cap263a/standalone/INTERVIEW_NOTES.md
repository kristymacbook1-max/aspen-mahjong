# Interview spec — coverage notes

`interview_spec.json` mirrors `taxonomy/interview.yaml` / `interview.py`'s
Phase E question graph (gates 0-10) plus a new `gateT` (tangible-property
elections, grounded in `engines/tangible_263a.py`, not in interview.py).

## Validation (re-run against the live code, not just at generation time)

- 78 questions across 12 gates; every `show_if` (including `in`/`any`/
  `derived` forms) resolves to a real question id or a real derived name
  (`small_business_exempt`, `under_448c_threshold`, `srm_available`).
- Every `maps_to.profile_field` is a real `EntityProfile` dataclass field
  (checked by importing the class and diffing against
  `dataclasses.fields`).
- Every choice-type question's `show_if`/`in` values are members of that
  question's own `choices` list.
- `requires_schedule_if.schedule` values match the app's schedule kinds
  (`btd`, `fixed_assets`, `cip`, `debt`, `re`, `transaction_costs`,
  `intangibles`, `startup`, `qualified_expenditures`, plus `ppa` for the
  §1060 purchase-price-allocation schedule, which `run_engagement`'s
  `present` dict does not track but the standalone app models as its own
  tab).

Zero validation errors as of this build.

## Completeness rules → engine warning codes

Each `completeness` entry exists to ask a question BEFORE computing that an
engine would otherwise only surface as a warning AFTER computing:

| Completeness rule | Engine warning it preempts |
| --- | --- |
| LIFO + MSPM missing increment | `MSPM-LIFO-INCREMENT-MISSING` |
| HAR elected, ratios missing | `HAR-RATIOS-MISSING` |
| MSPM labor split, proportion missing | `MSPM-SPLIT-INPUT-MISSING` |
| SRM variation B, total LIFO figure missing | `SRM-VARIATION-B-INPUT-MISSING` |
| Producer, activity level unknown | `SRM-PRODUCTION-LEVEL-UNKNOWN` |
| No nontraced debt / no AFR | `WAIR-UNAVAILABLE` |

## Intentional omissions

- The department-level (g)(4)(ii) 90/10 mechanics are not asked about beyond
  the existing flag question — the engine doesn't compute the department
  carve-out either (`MSC-90-10-NOT-IMPLEMENTED`), so a deeper interview
  branch would ask for facts nothing downstream uses.
- §1.263A-10 unit-of-property/common-feature combination and §1.263A-11(c)
  contract-payment APE have no questions — out of scope for both the engine
  and the interview (flag-only in the engine).
- No interview.py answer was found without an `EntityProfile`/flag
  destination; nothing was silently dropped.
