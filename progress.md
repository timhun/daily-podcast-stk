# Progress Log

## 2025-10-31
- Task: Strategy layer PK integration (Task Card 1).
- Updates: Enabled multi-strategy execution in `main.py` (GodSystemStrategy + BigLineStrategy) with sentiment enrichment; added per-strategy summaries in `content_creator.py`; hardened `BigLineStrategy` for missing sentiment; refreshed README to describe the PK output.
- Notes: Strategy results now expose both the best pick and raw per-strategy metrics for downstream consumers.
