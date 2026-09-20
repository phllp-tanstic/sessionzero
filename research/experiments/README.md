# Experiment registry

The append-only private registry is `.local-data/research/experiments/<experiment_id>/`.
Each entry has `result.json` and `records.json`, mode 0600. The runner verifies identical reruns
and refuses conflicting results. Earlier source-version runs are retained, including development
iterations. `verification.json` is a generated receipt pointing to the canonical verified runs;
it contains no raw prices or diagnostic performance metrics. Do not publish private outputs while
derived-data rights remain unverified. See `docs/RESEARCH_PROTOCOL.md` for reproduction and limits.
