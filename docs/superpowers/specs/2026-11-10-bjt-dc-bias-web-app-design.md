# BJT DC Bias Web App — Design

**Course:** ENG29 2121 · Lab 02 · 2/2569
**Date:** 2026-11-10
**Status:** Awaiting approval

---

## 1. Intent and why

Lab 02 requires a **real multi-file Flask web application** that computes the DC
operating point of an NPN BJT in a Common-Emitter **voltage-divider bias**
circuit. The point of the exercise is not the arithmetic — it is to show that a
web page with a Python backend is a different thing from an HTML file opened
with `file://`. The student must be able to explain where the calculation
happens, and prove the numbers are right.

Success is a running app on `http://127.0.0.1:5000/` that a marker can open,
type values into, and get correct DC results from — with automated tests that
fail if the engineering logic breaks.

---

## 2. Goals

| # | Goal |
|---|---|
| G1 | `GET /` returns an input form with HTTP 200 (Acceptance A1) |
| G2 | `POST /calculate` computes results in Python and renders them as HTML (A2) |
| G3 | Results match an independent hand calculation under the same model (A3) |
| G4 | Bad input produces readable field errors without crashing (A4) |
| G5 | Results outside the forward-active assumption carry a warning (A5) |
| G6 | ≥3 unit tests on the math + ≥1 test through the Flask test client (A6) |
| G7 | A fresh clone installs and runs per README (A7) |

## 3. Non-goals

- AC small-signal analysis, gain, Bode plots, transient response
- SPICE / ngspice integration, DC load line
- Bias templates beyond voltage divider (fixed bias, emitter bias, …)
- FET / MOSFET support
- Interactive schematic editor, animated overlays
- Database, authentication, deployment, Session state
- Client-side calculation — the browser must never compute the answer

## 4. Anti-goals

These would be failures even if the page "works":

- Numbers typed into the HTML template as fixed text
- Physics equations embedded in `templates/index.html` or in JavaScript
- A page that throws a 500 traceback when a field is blank
- Reporting a DC operating point with no warning when the transistor is
  saturated or cut off — that presents a model failure as a valid result
- Any single-file `.html` deliverable

---

## 5. Approaches considered

**A · Single page, `POST /` only.** Form and results in one template, one route.
Cheapest to build, but the form and the calculation can only be tested through
the same endpoint, so one broken thing hides another.

**B · `GET /` + `POST /calculate`.** *(chosen)* Two routes with separate
responsibilities. A1 (form renders) and A2 (calculation works) become
independently testable. Costs one extra route and one extra test.

**C · JSON API + `fetch()`.** Rejected: the lab explicitly requires the Python
backend to render HTML, and client-side JS adds failure modes that cannot be
afforded in a 75-minute build window.

**Chosen: B.** Rubric weight sits on logic, validation and tests (4 of 10
points). Two independently testable routes protect more of that weight.

**Not a choice:** the Forward-Active approximation with constant β and constant
V_BE, solved by direct substitution. Not an iterative solver, not SPICE. The lab
mandates this model.

---

## 6. The circuit and the model

NPN common emitter, voltage-divider bias:

- `R1` from VCC to base, `R2` from base to ground
- `RC` from VCC to collector, `RE` from emitter to ground

Equations, evaluated in this order:

```
VTH = VCC * R2 / (R1 + R2)
RTH = R1 * R2 / (R1 + R2)
IB  = (VTH - VBE) / (RTH + (beta + 1) * RE)
IC  = beta * IB
IE  = (beta + 1) * IB
VE  = IE * RE
VB  = VE + VBE
VC  = VCC - IC * RC
VCE = VC - VE
```

Resistance inputs arrive in **kΩ** and are converted to Ω before use.
Voltages are volts, currents are amperes internally.

### 6.1 Operating region

| Condition | Region | Behaviour |
|---|---|---|
| `VTH <= VBE` | `CUTOFF` | Base current would be ≤ 0. Report `IB = IC = IE = 0`, `VE = 0`, `VB = VTH`, `VC = VCC`, `VCE = VCC`, and warn that the model does not apply. `VTH` and `RTH` are still displayed. |
| `VCE < 0.3 V` | `SATURATION` | Show the forward-active numbers, but mark the result unreliable and warn that the assumption is violated. Do **not** re-solve. |
| otherwise | `ACTIVE` | Show numbers. If `VCE < 0.7 V`, add a non-fatal caution that the point is near saturation. |

**Builder's call, settled:** in cutoff `VB = VTH`, because with no base current
the divider alone sets the base node. `VB = VBE` would contradict the cutoff
condition itself. `VTH`/`RTH` remain visible because they explain *why* the
transistor is off.

Region labels are uppercase strings; warnings are a list of human-readable
strings rendered as a banner.

---

## 7. Routes

| Route | Method | Behaviour |
|---|---|---|
| `/` | GET | Render `index.html` with empty errors, form pre-filled with the lab sample values, no results block |
| `/calculate` | POST | Read the form, validate, compute, render `index.html` with results and/or errors |

Validation failures return **HTTP 200** with the form re-rendered and
field-level messages. Not 400, not a redirect — the page must stay alive and
the user's entered values must be preserved.

One template (`templates/index.html`) serves both states. Results and error
blocks are conditional on the context.

---

## 8. Inputs

| Field | Name | Unit | Default |
|---|---|---|---|
| Supply voltage | `vcc` | V | 12 |
| Base–VCC resistor | `r1` | kΩ | 100 |
| Base–GND resistor | `r2` | kΩ | 22 |
| Collector resistor | `rc` | kΩ | 2.2 |
| Emitter resistor | `re` | kΩ | 1 |
| Current gain | `beta` | — | 100 |
| Base–emitter drop | `vbe` | V | 0.70 |

All seven are **required** and must parse as finite floats. Accepted syntax:
plain decimals and exponential notation. A leading `+`/`-` is accepted; the
value rules below then reject out-of-range numbers.

## 9. Validation rules

| Field | Rule | Message intent |
|---|---|---|
| any | missing or not a number | "must be a number" |
| `vcc` | `> 0` | "must be greater than zero" |
| `r1`, `r2`, `rc`, `re` | `> 0` | "must be greater than zero" |
| `beta` | `> 0` | "must be greater than zero" |
| `vbe` | `> 0` and `< vcc` | "must be between 0 and VCC" |

Errors are collected per field so several can be shown at once. A field with an
error keeps its raw submitted text in the re-rendered form.

## 10. Outputs

Shown with units, in this order:

- Intermediate, for teaching: `VTH` [V], `RTH` [kΩ]
- `VB`, `VE`, `VC`, `VCE` [V] to 3 decimals
- `IC`, `IE` [mA] and `IB` [µA] to 3 decimals
- Region badge: `ACTIVE` / `SATURATION` / `CUTOFF`
- Warning banner when `warnings` is non-empty

---

## 11. File layout

```
BJT DC Bias Web App/
├── app.py                    # Flask app, routes, form parsing, error rendering
├── dc_bias.py                # pure engineering: validation-free math, no Flask, no HTML
├── templates/
│   └── index.html            # form + conditional results/errors
├── static/
│   └── style.css             # layout and presentation
├── tests/
│   ├── test_dc_bias.py       # engineering math (unittest)
│   └── test_web.py           # Flask test client (unittest)
├── requirements.txt          # Flask only
├── README.md                 # install, run, test
├── AGENTS.md                 # AI coding conventions for this repo
├── .gitignore                # .venv/, __pycache__/, .env, *.pyc
├── docs/
│   ├── design-note.md
│   ├── validation.md
│   ├── reflection.md
│   └── superpowers/specs/2026-11-10-bjt-dc-bias-web-app-design.md
```

### 11.1 Module boundaries

- `dc_bias.py` must not import Flask. It exposes a calculation entry point that
  takes numeric values and returns a result object; it raises on invalid
  numeric input (e.g. `ValueError`) and never formats HTML.
- `app.py` owns HTTP: reading `request.form`, converting strings to numbers,
  turning exceptions into field errors, choosing the template and status code.
- `templates/index.html` contains no physics. It only displays what the context
  gives it.
- `tests/test_dc_bias.py` imports only `dc_bias`. `tests/test_web.py` imports
  only `app`.

### 11.2 Unit contract for `dc_bias`

Settled here so the module API and the math tests agree:

- **In:** `vcc` [V], `r1`, `r2`, `rc`, `re` [**kΩ**], `beta` [—], `vbe` [V]
- **Out:** `vth`, `vb`, `ve`, `vc`, `vce` [V]; `rth` [**kΩ**];
  `ib`, `ic`, `ie` [**A**]
- Conversion kΩ → Ω happens once, inside `dc_bias`, before the equations run.
- `app.py` converts amperes to mA/µA for display only. Tests assert `IC`
  against amperes (e.g. `1.230e-3`), not against mA, so a unit slip cannot pass
  silently.

### 11.3 Required documentation files

All three are deliverables, written in Thai, roughly one page each:

| File | Content |
|---|---|
| `docs/design-note.md` | Why this app exists, scope and non-goals, chosen architecture (route B), the equations, and the region rules — derived from this design doc, short enough to read in two minutes |
| `docs/validation.md` | The worked hand calculation for the sample values (A3), a table of invalid-input cases and what the page shows (A4), the cutoff and saturation cases with the warning text (A5), and the passing test log (A6) |
| `docs/reflection.md` | What was learned, and short answers to the four personal questions in the handout (why `file://` is not Flask, how the form reaches Python, whether `dc_bias.py` changes require HTML changes, why a warning is mandatory outside the model's region) |

Grading does not demand a specific length or structure for these; they must
exist, be accurate, and match what the code actually does. Any claims in them
must come from a real run, not from intention.


---

## 12. Tests

Test runner is **`unittest`**, matching the lab command
`python -m unittest discover -s tests -v`. No pytest dependency.

### `tests/test_dc_bias.py` (minimum 4)

1. **Sample point.** VCC=12, R1=100k, R2=22k, RC=2.2k, RE=1k, β=100,
   VBE=0.70 → VB≈1.942 V, VE≈1.242 V, VC≈9.294 V, VCE≈8.052 V,
   IC≈1.230 mA, region `ACTIVE` (tolerance 1e-3).
2. **Bias network.** VTH≈2.164 V and RTH≈18.033 kΩ for the same inputs.
3. **Cutoff.** R2 small enough that VTH ≤ VBE → region `CUTOFF`, IC=0,
   warning present.
4. **Saturation.** RC large enough that VCE < 0.3 V → region `SATURATION`,
   warning present.
5. **Rejects bad numeric input** (`R=0`, `beta=0`, negative VCC) by raising.

### `tests/test_web.py` (minimum 3)

1. `GET /` → 200, contains the seven input names and a submit control.
2. `POST /calculate` with the sample values → 200, body contains the expected
   voltages (asserts the number came from Python, not the template).
3. `POST /calculate` with `r1=0` → 200, body contains an error message, no
   traceback.
4. `POST /calculate` with `vcc=abc` → 200, body contains "must be a number".

---

## 13. Constraints

- **Governing spec.** The lab handout
  (`Lab02_BJT_Simulator_Brainstorm_2-2569.html`, provided by the course) is the
  authority on requirements and grading. This document is authoritative wherever
  it is more specific than the handout. Where the handout leaves a detail open,
  the builder decides and writes the decision down.
- Python 3.14, Flask 3.1, standard library otherwise
- `unittest` only; the lab runs `python -m unittest discover -s tests -v`
- Dev server only: `python -m flask --app app run --debug`, localhost
- `.venv/` must never be committed
- UI language: Thai labels with English technical terms. Exact Thai wording is
  the builder's to author, using the handout's vocabulary
- Styling is deliberately plain: readable, responsive, no animation, no images

## 14. Left to the builder

- Exact wording of error, warning and Thai UI label text
- Colour palette and spacing within `static/style.css`
- Whether helper text under each field is present
- Internal function/class names and the result container type
- Number formatting helper implementation
- README phrasing
- Whether to add `tests/__init__.py` (unittest discovery works without it)


## 15. Done means

All of A1–A7 pass in a browser and in the terminal, `python -m unittest
discover -s tests -v` is green, and the working tree is committed with a
readable message. No cell in the acceptance table is satisfied by hard-coded
text.
