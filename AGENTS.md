# AGENTS.md — conventions for this repository

Read before changing anything here.

## Boundaries

- `dc_bias.py` must never import Flask, HTML, or `app`. It is the only place
  physics lives.
- `app.py` owns HTTP: reading the form, converting strings to numbers, turning
  problems into field errors, choosing a template and a status code.
- `templates/index.html` contains no equations. It displays what the context
  gives it.
- `tests/test_dc_bias.py` imports only `dc_bias`. `tests/test_web.py` imports
  only `app`.

## Units

- Every resistance parameter crossing into `dc_bias` is in **kilohms** and is
  named with a `_k` suffix.
- `dc_bias` returns `rth` in kilohms and `ib` / `ic` / `ie` in **amperes**.
- `app.py` converts amperes to mA / µA for display only.
- Tests assert currents in amperes, so a unit slip fails by three orders of
  magnitude instead of passing quietly.

## Testing

- Runner is `unittest`. Do not add pytest.
- Full suite: `python -m unittest discover -s tests -v`
- Every change starts with a failing test. Watch it fail for the right reason
  before writing the implementation.

## Behaviour that must not regress

- Invalid input returns **HTTP 200** with field errors. Never 400, never a
  traceback.
- Typed values survive a failed submit.
- `VTH <= VBE` reports `CUTOFF` with zero currents and `VB = VTH`.
- `VCE < 0.3 V` reports `SATURATION` with a warning. `0.3–0.7 V` reports
  `ACTIVE` with a caution.

## Commit hygiene

- `.venv/`, `__pycache__/`, `.superpowers/` and `.env` are never committed.
- Commits are made through GitHub Desktop by the human partner.
