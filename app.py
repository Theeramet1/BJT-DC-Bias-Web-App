"""Flask front end for the BJT DC bias calculator.

The engineering lives in :mod:`dc_bias`. This module owns HTTP only: reading
the form, turning problems into readable messages, and choosing a template.
"""

import math

from flask import Flask, render_template, request

import dc_bias

app = Flask(__name__)

DEFAULTS = {
    "mode": "divider",
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "rb": "1000",
    "beta": "100",
    "vbe": "0.70",
}

FIELD_LABELS = {
    "vcc": "VCC [V]",
    "r1": "R1 [kΩ]",
    "r2": "R2 [kΩ]",
    "rc": "RC [kΩ]",
    "re": "RE [kΩ]",
    "rb": "RB [kΩ]",
    "beta": "β (hFE)",
    "vbe": "VBE [V]",
}

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

# Fields required for each mode (all in kΩ except vcc, beta, vbe)
MODE_FIELDS = {
    "divider": ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    "fixed": ("vcc", "rb", "rc", "beta", "vbe"),
    "emitter": ("vcc", "rb", "re", "rc", "beta", "vbe"),
}

POSITIVE_FIELDS = ("vcc", "r1", "r2", "rc", "re", "rb", "beta")


def parse_form(form):
    """Return ``(values, errors)`` for a submitted form.

    ``values`` holds only the fields that survived validation. ``errors`` maps
    a field name to a message the user can act on.
    """
    mode = (form.get("mode") or "divider").strip()
    if mode not in MODE_FIELDS:
        return {}, {"mode": "โหมดวงจรไม่ถูกต้อง"}

    values = {"mode": mode}
    errors = {}

    required = MODE_FIELDS[mode]

    for name in required:
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
    mode = request.args.get("mode", "divider")
    if mode not in MODE_FIELDS:
        mode = "divider"
    form = dict(DEFAULTS)
    form["mode"] = mode
    return render_template(
        "index.html",
        form=form,
        errors={},
        result=None,
        labels=FIELD_LABELS,
        modes=MODE_FIELDS,
        mode_labels=MODE_LABELS,
        selected_mode=mode,
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
            modes=MODE_FIELDS,
            mode_labels=MODE_LABELS,
            selected_mode=values.get("mode", "divider"),
        )

    mode = values["mode"]
    try:
        if mode == "divider":
            result = dc_bias.divider_bias(
                vcc=values["vcc"],
                r1_k=values["r1"],
                r2_k=values["r2"],
                rc_k=values["rc"],
                re_k=values["re"],
                beta=values["beta"],
                vbe=values["vbe"],
            )
        elif mode == "fixed":
            result = dc_bias.fixed_bias(
                vcc=values["vcc"],
                rb_k=values["rb"],
                rc_k=values["rc"],
                beta=values["beta"],
                vbe=values["vbe"],
            )
        elif mode == "emitter":
            result = dc_bias.emitter_bias(
                vcc=values["vcc"],
                rb_k=values["rb"],
                re_k=values["re"],
                rc_k=values["rc"],
                beta=values["beta"],
                vbe=values["vbe"],
            )
        else:
            raise ValueError(f"โหมดวงจรไม่รองรับ: {mode}")
    except ValueError as exc:
        return render_template(
            "index.html",
            form=request.form,
            errors={},
            form_error=str(exc),
            result=None,
            labels=FIELD_LABELS,
            modes=MODE_FIELDS,
            mode_labels=MODE_LABELS,
            selected_mode=mode,
        )

    return render_template(
        "index.html",
        form=request.form,
        errors={},
        result=result,
        mode=mode,
        labels=FIELD_LABELS,
        modes=MODE_FIELDS,
        mode_labels=MODE_LABELS,
        selected_mode=mode,
    )
