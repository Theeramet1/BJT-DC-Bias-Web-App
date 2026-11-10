"""Flask front end for the BJT DC bias calculator.

The engineering lives in :mod:`dc_bias`. This module owns HTTP only: reading
the form, turning problems into readable messages, and choosing a template.
"""

import math

from flask import Flask, render_template, request

import dc_bias

app = Flask(__name__)

DEFAULTS = {
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "beta": "100",
    "vbe": "0.70",
}

FIELD_LABELS = {
    "vcc": "VCC [V]",
    "r1": "R1 [kΩ]",
    "r2": "R2 [kΩ]",
    "rc": "RC [kΩ]",
    "re": "RE [kΩ]",
    "beta": "β (hFE)",
    "vbe": "VBE [V]",
}

POSITIVE_FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta")


def parse_form(form):
    """Return ``(values, errors)`` for a submitted form.

    ``values`` holds only the fields that survived validation. ``errors`` maps
    a field name to a message the user can act on.
    """
    values = {}
    errors = {}

    for name in FIELD_LABELS:
        raw = (form.get(name) or "").strip()
        if not raw:
            errors[name] = "กรุณากรอกค่านี้"
            continue
        try:
            number = float(raw)
        except ValueError:
            errors[name] = "ต้องเป็นตัวเลข"
            continue
        if not math.isfinite(number):
            errors[name] = "ต้องเป็นตัวเลข"
            continue
        values[name] = number

    for name in POSITIVE_FIELDS:
        if name in values and values[name] <= 0:
            errors[name] = "ต้องมากกว่า 0"

    if "vbe" in values:
        vbe = values["vbe"]
        vcc = values.get("vcc")
        if vbe <= 0:
            errors["vbe"] = "ต้องมากกว่า 0"
        elif vcc is not None and vbe >= vcc:
            errors["vbe"] = "ต้องอยู่ระหว่าง 0 ถึง VCC"

    for name in errors:
        values.pop(name, None)

    return values, errors


@app.get("/")
def index():
    """Render the input form filled with the lab's sample values."""
    return render_template(
        "index.html",
        form=DEFAULTS,
        errors={},
        result=None,
        labels=FIELD_LABELS,
    )


@app.post("/calculate")
def calculate():
    """Compute the DC operating point and render it alongside the form."""
    values, errors = parse_form(request.form)

    if errors:
        return render_template(
            "index.html",
            form=request.form,
            errors=errors,
            result=None,
            labels=FIELD_LABELS,
        )

    try:
        result = dc_bias.operating_point(
            vcc=values["vcc"],
            r1_k=values["r1"],
            r2_k=values["r2"],
            rc_k=values["rc"],
            re_k=values["re"],
            beta=values["beta"],
            vbe=values["vbe"],
        )
    except ValueError as exc:
        return render_template(
            "index.html",
            form=request.form,
            errors={},
            form_error=str(exc),
            result=None,
            labels=FIELD_LABELS,
        )

    return render_template(
        "index.html",
        form=request.form,
        errors={},
        result=result,
        labels=FIELD_LABELS,
    )
