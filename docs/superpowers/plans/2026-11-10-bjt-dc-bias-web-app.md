# BJT DC Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a multi-file Flask app that computes the DC operating point of an NPN voltage-divider-biased common-emitter stage, with validation, region warnings, and automated tests.

**Architecture:** `dc_bias.py` holds pure engineering math and knows nothing about HTTP or HTML. `app.py` owns the two routes (`GET /`, `POST /calculate`), parses the form, turns errors into field messages, and renders a single Jinja template. Tests split along the same boundary: one file for the math, one for the HTTP layer.

**Tech Stack:** Python 3.14, Flask 3.1, `unittest` (no pytest)

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-web-app-design.md`

## Global Constraints

- Python 3.14, Flask 3.1; standard library otherwise
- Test runner is `unittest`. Never add pytest. Full suite: `python -m unittest discover -s tests -v`
- Resistor inputs are **kΩ**; `dc_bias` converts to Ω once, before the equations
- `dc_bias` returns `rth` in **kΩ** and `ib`/`ic`/`ie` in **amperes**
- `dc_bias.py` must not import Flask, HTML, or `app`
- Routes are exactly `GET /` and `POST /calculate`
- Invalid input returns **HTTP 200** with field errors; never a 400, never a traceback
- `.venv/`, `__pycache__/`, `.env`, `*.pyc` are never committed
- UI text is Thai with English technical terms
- Region labels are the uppercase strings `ACTIVE`, `SATURATION`, `CUTOFF`
- Commits are made by the human partner through GitHub Desktop; the executor prepares the working tree and reports, but does not run `git commit`

## Review Focus

Failure modes the spec implies but no happy-path test pins down. Each gets a test in the task that owns the code.

1. `" 12 "` (surrounding whitespace) — a person pastes from a spreadsheet; must be accepted, not rejected
2. `"2,2"` (comma decimal) — a Thai keyboard habit; must produce a readable error, not a traceback
3. `"1e400"` — parses to `inf`; must be rejected as not a finite number
4. Empty form submitted — all seven fields report errors, page still returns 200
5. `beta = 10000` with the sample resistors — drives `VCE` negative; must report `SATURATION` and still render the page

---

## File Structure

| File | Responsibility |
|---|---|
| `dc_bias.py` | Bias network and operating-point math, region classification, warnings. Raises `ValueError` on non-physical input. No Flask. |
| `app.py` | Flask app, form parsing, field errors, template rendering, status codes |
| `templates/index.html` | Form plus conditional results/error/region blocks. No equations. |
| `static/style.css` | Layout and presentation only |
| `tests/test_dc_bias.py` | Math tests, imports only `dc_bias` |
| `tests/test_web.py` | HTTP tests via Flask test client, imports only `app` |
| `tests/__init__.py` | Empty, enables `python -m unittest tests.test_x` |
| `requirements.txt` | `Flask>=3.1` |
| `.gitignore` | Venv and Python artefacts |
| `README.md` | Install, run, test — A7 |
| `AGENTS.md` | Conventions for AI edits to this repo |
| `docs/design-note.md`, `docs/validation.md`, `docs/reflection.md` | Rubric deliverables |

---

### Task 1: Skeleton, hygiene, and the bias network

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `tests/__init__.py`
- Create: `dc_bias.py`
- Create: `tests/test_dc_bias.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `dc_bias.KOHM: float` (= 1000.0)
  - `dc_bias.bias_network(vcc: float, r1_k: float, r2_k: float) -> tuple[float, float]` returning `(vth_volts, rth_kohm)`

- [ ] **Step 1: Write the failing test**

`tests/test_dc_bias.py`:

```python
import unittest

import dc_bias


class BiasNetworkTests(unittest.TestCase):
    def test_divider_network_for_sample_values(self):
        vth, rth = dc_bias.bias_network(12.0, 100.0, 22.0)
        self.assertAlmostEqual(vth, 2.163934, places=5)
        self.assertAlmostEqual(rth, 18.032787, places=5)

    def test_equal_resistors_halve_the_supply(self):
        vth, rth = dc_bias.bias_network(10.0, 10.0, 10.0)
        self.assertAlmostEqual(vth, 5.0)
        self.assertAlmostEqual(rth, 5.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dc_bias'`

- [ ] **Step 3: Create the supporting files and `dc_bias.bias_network`**

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
.env
.DS_Store
```

`requirements.txt`:

```
Flask>=3.1
```

`tests/__init__.py`: empty file.

`dc_bias.py` — module docstring states the model is the forward-active approximation with constant β and constant V_BE, and that inputs are kΩ. Implement:

```python
KOHM = 1000.0


def bias_network(vcc: float, r1_k: float, r2_k: float) -> tuple[float, float]:
    """Return (VTH in volts, RTH in kΩ) for the voltage-divider bias network."""
```

`VTH = vcc * r2_k / (r1_k + r2_k)`, `RTH_k = r1_k * r2_k / (r1_k + r2_k)`. The kΩ/Ω factor cancels in both expressions, so `RTH` is naturally in kΩ — do not multiply by `KOHM` here.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: `OK` with 2 tests, `Ran 2 tests`

- [ ] **Step 5: Report for commit**

Tell the human partner these files are ready in GitHub Desktop's Changes tab. Do not run `git commit`.

---

### Task 2: Operating point, region classification, warnings

**Files:**
- Modify: `dc_bias.py`
- Test: `tests/test_dc_bias.py` (append)

**Interfaces:**
- Consumes: `dc_bias.bias_network(vcc, r1_k, r2_k)`
- Produces:
  - `dc_bias.BiasResult` — dataclass with fields `vth: float` (V), `rth: float` (kΩ), `ib: float` (A), `ic: float` (A), `ie: float` (A), `vb: float` (V), `ve: float` (V), `vc: float` (V), `vce: float` (V), `region: str`, `warnings: tuple[str, ...]`
  - `dc_bias.operating_point(vcc: float, r1_k: float, r2_k: float, rc_k: float, re_k: float, beta: float, vbe: float) -> BiasResult`
  - `dc_bias.VCE_SATURATION: float` (= 0.3), `dc_bias.VCE_NEAR_SATURATION: float` (= 0.7)

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_dc_bias.py`:

```python
class OperatingPointTests(unittest.TestCase):
    def sample(self, **overrides):
        params = dict(
            vcc=12.0, r1_k=100.0, r2_k=22.0, rc_k=2.2, re_k=1.0,
            beta=100.0, vbe=0.70,
        )
        params.update(overrides)
        return dc_bias.operating_point(**params)

    def test_sample_values_match_hand_calculation(self):
        r = self.sample()
        self.assertAlmostEqual(r.vth, 2.163934, places=5)
        self.assertAlmostEqual(r.rth, 18.032787, places=5)
        self.assertAlmostEqual(r.ib, 12.299e-6, delta=1e-9)
        self.assertAlmostEqual(r.ic, 1.230e-3, delta=1e-9)
        self.assertAlmostEqual(r.ie, 1.242e-3, delta=1e-9)
        self.assertAlmostEqual(r.ve, 1.242, places=3)
        self.assertAlmostEqual(r.vb, 1.942, places=3)
        self.assertAlmostEqual(r.vc, 9.294, places=3)
        self.assertAlmostEqual(r.vce, 8.052, places=3)
        self.assertEqual(r.region, "ACTIVE")

    def test_cutoff_reports_zero_currents_and_divider_base(self):
        r = self.sample(r2_k=5.0)
        self.assertEqual(r.region, "CUTOFF")
        self.assertEqual(r.ib, 0.0)
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.ie, 0.0)
        self.assertEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vb, 12.0 * 5.0 / 105.0, places=5)
        self.assertEqual(r.vc, 12.0)
        self.assertEqual(r.vce, 12.0)
        self.assertAlmostEqual(r.vth, 12.0 * 5.0 / 105.0, places=5)
        self.assertTrue(r.warnings)

    def test_large_collector_resistor_is_reported_as_saturation(self):
        r = self.sample(rc_k=15.0)
        self.assertEqual(r.region, "SATURATION")
        self.assertTrue(r.warnings)
        self.assertLess(r.vce, dc_bias.VCE_SATURATION)

    def test_point_just_above_saturation_stays_active_with_caution(self):
        r = self.sample(rc_k=8.34)
        self.assertEqual(r.region, "ACTIVE")
        self.assertTrue(r.warnings)
        self.assertGreater(r.vce, dc_bias.VCE_SATURATION)
        self.assertLess(r.vce, dc_bias.VCE_NEAR_SATURATION)

    def test_very_high_beta_drives_the_stage_into_saturation(self):
        r = self.sample(beta=10000.0)
        self.assertEqual(r.region, "SATURATION")
        self.assertTrue(r.warnings)

    def test_rejects_non_physical_parameters(self):
        for bad in (
            dict(vcc=0.0), dict(vcc=-1.0), dict(r1_k=0.0), dict(r2_k=0.0),
            dict(rc_k=0.0), dict(re_k=0.0), dict(beta=0.0), dict(beta=-5.0),
            dict(vbe=0.0), dict(vbe=12.0), dict(vbe=20.0),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.sample(**bad)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: FAIL — `AttributeError: module 'dc_bias' has no attribute 'operating_point'`

- [ ] **Step 3: Implement the operating point in `dc_bias.py`**

Add `BiasResult` (frozen dataclass), the two constants, and `operating_point`. Steps inside it, in this order:

1. Validate: every resistor, `vcc`, `beta` must be `> 0`; `vbe` must satisfy `0 < vbe < vcc`. Raise `ValueError` with a message naming the offending parameter.
2. `vth, rth_k = bias_network(vcc, r1_k, r2_k)`
3. If `vth <= vbe` → cutoff branch: return `ib=ic=ie=ve=0.0`, `vb=vth`, `vc=vcc`, `vce=vcc`, `region="CUTOFF"`, one warning explaining the base is not forward biased so the forward-active model does not apply.
4. Otherwise forward active: `ib = (vth - vbe) / (rth_k * KOHM + (beta + 1) * re_k * KOHM)` — note both denominator terms are in Ω. Then `ic = beta * ib`, `ie = (beta + 1) * ib`, `ve = ie * re_k * KOHM`, `vb = ve + vbe`, `vc = vcc - ic * rc_k * KOHM`, `vce = vc - ve`.
5. Region: `vce < VCE_SATURATION` → `"SATURATION"` with a warning that the Forward-Active assumption is violated and the numbers are not trustworthy. `VCE_SATURATION <= vce < VCE_NEAR_SATURATION` → `"ACTIVE"` with a caution that the point is close to saturation. Otherwise `"ACTIVE"` with no warnings.
6. `warnings` is always a tuple, empty when nothing applies.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_dc_bias -v`
Expected: `Ran 8 tests`, `OK`

- [ ] **Step 5: Report for commit**

---

### Task 3: Flask app and the input form

**Files:**
- Create: `app.py`
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `tests/test_web.py`

**Interfaces:**
- Consumes: nothing from `dc_bias` yet
- Produces:
  - Module-level `app` in `app.py` (a `Flask` instance) — required by `python -m flask --app app run`
  - `app.DEFAULTS: dict[str, str]` — the pre-filled form values
  - `app.FIELD_LABELS: dict[str, str]` — Thai labels
  - Template context keys `form`, `errors`, `result`

- [ ] **Step 1: Write the failing test**

`tests/test_web.py`:

```python
import unittest

import app as webapp


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()

    def test_get_root_serves_the_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for name in ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"):
            self.assertIn(f'name="{name}"', body)
        self.assertIn("<form", body)
        self.assertIn("type=\"submit\"", body)

    def test_form_is_prefilled_with_the_sample_values(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('value="100"', body)
        self.assertIn('value="0.70"', body)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_web -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Implement `app.py`, `templates/index.html`, `static/style.css`**

`app.py`:

```python
app = Flask(__name__)

DEFAULTS = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
            "beta": "100", "vbe": "0.70"}
FIELD_LABELS = {"vcc": "VCC [V]", "r1": "R1 [kΩ]", "r2": "R2 [kΩ]",
                "rc": "RC [kΩ]", "re": "RE [kΩ]", "beta": "β (hFE)",
                "vbe": "VBE [V]"}


@app.get("/")
def index():
    """Render the form with sample defaults and no results."""
```

`templates/index.html` must contain a `<form method="post" action="/calculate">`, one labelled input per field in `FIELD_LABELS` order, and a submit button. Wrap fields in `<label>` with the Thai label text from `FIELD_LABELS`; add a unit hint next to the label rather than inventing a unit selector. Add `{{ url_for('static', filename='style.css') }}` in `<head>`. Leave placeholders for `{% if errors %}`, `{% if result %}`, and `{% if result.warnings %}` blocks — empty for now, filled in Tasks 4 and 5.

`static/style.css`: single centred card, max-width around 720px, readable font size, visible focus states. No animation, no images, no external fonts.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_web -v`
Expected: `Ran 2 tests`, `OK`

- [ ] **Step 5: Report for commit**

---

### Task 4: `POST /calculate` happy path

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`
- Test: `tests/test_web.py` (append)

**Interfaces:**
- Consumes: `dc_bias.operating_point(...)`, `dc_bias.BiasResult`
- Produces: `app.calculate()` bound to `POST /calculate`, rendering `index.html` with a `result` in context

- [ ] **Step 1: Write the failing test**

Append to `tests/test_web.py`:

```python
class CalculateTests(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.valid = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                      "re": "1", "beta": "100", "vbe": "0.70"}

    def test_sample_input_renders_the_computed_operating_point(self):
        response = self.client.post("/calculate", data=self.valid)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("1.942", body)
        self.assertIn("9.294", body)
        self.assertIn("8.052", body)
        self.assertIn("ACTIVE", body)

    def test_numbers_come_from_python_not_the_template(self):
        changed = dict(self.valid, vcc="15", r1="47")
        body = self.client.post("/calculate", data=changed).get_data(as_text=True)
        self.assertNotIn("1.942", body)
        self.assertIn("VCE", body)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_web -v`
Expected: FAIL — 404 on `POST /calculate`

- [ ] **Step 3: Implement the route**

```python
@app.post("/calculate")
def calculate():
    """Read the form, compute the operating point, render index.html."""
```

For this task the route may assume the input is valid: convert with `float(value.strip())`, call `dc_bias.operating_point(...)` using the kΩ field values directly, and render `index.html` with `result=result`, `form=request.form`, `errors={}`. No `try`/`except` yet — Task 5 adds it.

In `index.html`, fill the `{% if result %}` block: a definition list showing VTH [V], RTH [kΩ], VB, VE, VC, VCE [V] to 3 decimals, and IC, IE [mA] / IB [µA] to 3 decimals, then a region badge printing `{{ result.region }}`. Format numbers in Jinja with `'%.3f'|format(...)`; convert amperes with `* 1000` for mA and `* 1e6` for µA.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m unittest tests.test_web -v`
Expected: `Ran 4 tests`, `OK`

- [ ] **Step 5: Start the app and check by eye**

Run: `python -m flask --app app run --debug`
Open `http://127.0.0.1:5000/`, submit the defaults, confirm VB 1.942, VE 1.242, VC 9.294, VCE 8.052, IC 1.230 mA, region ACTIVE. Stop the server.

- [ ] **Step 6: Report for commit**

---

### Task 5: Validation and error rendering

**Files:**
- Modify: `app.py`
- Modify: `templates/index.html`
- Test: `tests/test_web.py` (append)

**Interfaces:**
- Consumes: the same fields as Task 4
- Produces:
  - `app.parse_form(form) -> tuple[dict[str, float], dict[str, str]]` returning `(values, errors)` where `values` holds only fields that parsed, and `errors` maps field name → message
  - `calculate()` renders with `errors` populated and `result=None` when `errors` is non-empty, status 200

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_web.py`:

```python
class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.valid = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
                      "re": "1", "beta": "100", "vbe": "0.70"}

    def post(self, **overrides):
        data = dict(self.valid)
        data.update({k: v for k, v in overrides.items()})
        return self.client.post("/calculate", data=data)

    def test_zero_resistor_is_reported_without_crashing(self):
        response = self.post(r1="0")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("มากกว่า", body)
        self.assertNotIn("Traceback", body)

    def test_non_numeric_supply_voltage_is_reported(self):
        body = self.post(vcc="abc").get_data(as_text=True)
        self.assertIn("ตัวเลข", body)

    def test_whitespace_around_a_number_is_accepted(self):
        body = self.post(vcc=" 12 ").get_data(as_text=True)
        self.assertIn("1.942", body)

    def test_comma_decimal_is_rejected_with_a_readable_error(self):
        body = self.post(rc="2,2").get_data(as_text=True)
        self.assertIn("ตัวเลข", body)
        self.assertNotIn("Traceback", body)

    def test_infinite_number_is_rejected(self):
        body = self.post(r1="1e400").get_data(as_text=True)
        self.assertIn("ตัวเลข", body)

    def test_empty_form_reports_every_field(self):
        response = self.client.post("/calculate", data={})
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertEqual(body.count('class="field-error"'), 7)

    def test_entered_values_survive_a_failed_submit(self):
        body = self.post(rc="oops", r2="33").get_data(as_text=True)
        self.assertIn('value="33"', body)
        self.assertIn('value="oops"', body)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_web -v`
Expected: FAIL — server raises or returns 500 on `r1=0`; `field-error` class absent

- [ ] **Step 3: Implement parsing and error rendering**

`parse_form` rules, applied in this order per field:

1. Missing or empty after `.strip()` → `"กรุณากรอกค่านี้"` (required)
2. `"ตัวเลข"` (must be a number) — raised when `float()` fails **or** the result is `inf`/`nan`. This covers `abc`, `2,2`, and `1e400` with one message.
3. Range: `vcc`, `r1`, `r2`, `rc`, `re`, `beta` must be `> 0` → `"ต้องมากกว่า 0"`; `vbe` must be `> 0` and `< vcc` → `"ต้องอยู่ระหว่าง 0 ถึง VCC"`

In `calculate()`: call `parse_form`; if `errors` is non-empty render `index.html` with `errors`, `result=None`, and `form=request.form` (raw strings, so typed values survive). Otherwise call `dc_bias.operating_point(**values)` and render as in Task 4. Also catch `ValueError` from `dc_bias` and fold it into a form-level error so a logic slip can never produce a traceback.

In `index.html`: each input's `value` comes from `form.get(name, '')` so failed submits keep what the user typed; below each input render `{% if errors.get(name) %}<p class="field-error">{{ errors[name] }}</p>{% endif %}`. Render warnings from `result.warnings` as a list inside a `role="alert"` block.

- [ ] **Step 4: Run the full suite**

Run: `python -m unittest discover -s tests -v`
Expected: `Ran 15 tests`, `OK`

- [ ] **Step 5: Check the failure paths by eye**

Run the server, submit `r1=0`, then `rc=2,2`, then an empty form. Each must keep the page up, keep typed values, and show Thai messages. Stop the server.

- [ ] **Step 6: Report for commit**

---

### Task 6: README, AGENTS.md and the three rubric documents

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/design-note.md`
- Create: `docs/validation.md`
- Create: `docs/reflection.md`

**Interfaces:**
- Consumes: the finished app and its real test output
- Produces: documentation only — no code changes

- [ ] **Step 1: Write `README.md`**

Must contain, in order: what the app does and the model it uses; prerequisites (Python 3.14, Git); the exact setup block

```
python -m venv .venv
.venv\Scripts\Activate.ps1        # Windows PowerShell
python -m pip install -r requirements.txt
python -m flask --app app run --debug
# open http://127.0.0.1:5000/
python -m unittest discover -s tests -v
```

plus a note that the page must be served by Flask and cannot be opened with `file://`, the input units (kΩ, V), and the region rules. A fresh clone must be able to follow it verbatim.

- [ ] **Step 2: Write `AGENTS.md`**

Short conventions file: `dc_bias.py` never imports Flask; equations live only there; tests use `unittest`; inputs are kΩ; currents returned in A; run `python -m unittest discover -s tests -v` before claiming anything works.

- [ ] **Step 3: Write `docs/design-note.md`**

One page in Thai: purpose, scope and non-goals, route B and why, the equations, the region table. Derive from the spec, do not invent new rules.

- [ ] **Step 4: Write `docs/validation.md`**

Walk the sample values by hand: VTH 2.1639 V → RTH 18.033 kΩ → IB 12.299 µA → IC 1.230 mA → IE 1.242 mA → VE 1.242 V → VB 1.942 V → VC 9.294 V → VCE 8.052 V. Then tables for the invalid-input cases (A4) and the cutoff/saturation cases with their warning text (A5). Paste the **actual** `python -m unittest discover -s tests -v` output from Step 5, not a description of it.

- [ ] **Step 5: Run the suite and capture real output**

Run: `python -m unittest discover -s tests -v`
Expected: `Ran 15 tests`, `OK`. Paste this exact output into `validation.md`.

- [ ] **Step 6: Write `docs/reflection.md`**

Answers to the handout's four questions: why `file://` is not Flask; how the form reaches Python; whether changing an equation in `dc_bias.py` requires touching HTML; why results outside the forward-active region must carry a warning. Written from what this build actually did.

- [ ] **Step 7: Final check and report for commit**

Run `python -m unittest discover -s tests -v` once more, confirm `OK`, and tell the human partner everything is staged for a GitHub Desktop commit. Do not commit.

---

## Self-Review

**Spec coverage**

| Spec item | Task |
|---|---|
| G1 `GET /` 200 with form | 3 |
| G2 `POST /calculate` computes in Python | 4 |
| G3 matches hand calculation | 2 (math), 6 (validation.md) |
| G4 field errors, no crash | 5 |
| G5 region warnings | 2 (logic), 5 (rendering) |
| G6 ≥3 math + ≥1 HTTP test | 2 (8 math), 3–5 (15 total) |
| G7 clone-and-run per README | 6 |
| File layout §11 | 1, 3, 6 |
| Module boundaries §11.1 | 1–5 (enforced by test imports) |
| Unit contract §11.2 | 1 (kΩ→Ω), 2 (A out), 4 (display) |
| Docs §11.3 | 6 |
| Region table §6.1 | 2 |
| Validation table §9 | 5 |

**Step scan:** every step names a file, a command, or an exact assertion. No "handle edge cases" placeholders. Regions and error messages are given as literal strings so tests and UI cannot drift.

**Type consistency:** `bias_network` returns `(vth, rth_k)` and is consumed only by `operating_point`. `BiasResult.warnings` is a tuple; the template iterates it. `parse_form` returns `(values, errors)` and `calculate` reads only those two names. `values` keys are the seven raw field names, matching the `operating_point` parameter names after `_k` suffixes are added by the caller.

**Review Focus:** all five items carry a test — whitespace and comma and infinity and empty-form in Task 5, high-beta saturation in Task 2.
