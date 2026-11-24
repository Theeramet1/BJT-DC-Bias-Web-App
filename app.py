"""Flask front end for the BJT DC bias calculator.

The engineering lives in :mod:`dc_bias` (analytical) and :mod:`spice_engine`
(real ngspice runs). This module owns HTTP only: reading the form, turning
problems into readable messages, choosing a template and a status code.
"""

import math

from flask import Flask, render_template, request

import dc_bias
import spice_engine

app = Flask(__name__)

DEFAULTS = {
    "mode": "divider",
    "analysis": "analytical",
    "vcc": "12",
    "r1": "100",
    "r2": "22",
    "rc": "2.2",
    "re": "1",
    "rb": "1000",
    "rl": "10",
    "cin": "10",
    "cout": "10",
    "amplitude": "10",
    "frequency": "1000",
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
    "rl": "RL [kΩ]",
    "cin": "Cin [µF]",
    "cout": "Cout [µF]",
    "amplitude": "Source amplitude [mV]",
    "frequency": "Source frequency [Hz]",
    "beta": "β (hFE)",
    "vbe": "VBE [V]",
}

MODE_LABELS = {
    "divider": "Voltage Divider Bias",
    "fixed": "Fixed Bias",
    "emitter": "Emitter Bias",
}

ANALYSIS_LABELS = {
    "analytical": "DC Bias (analytical)",
    "spice_op": "DC Operating Point (ngspice .op)",
    "spice_ac": "AC Frequency Response (ngspice .ac)",
    "spice_tran": "Transient (ngspice .tran)",
}

# Fields required for each mode (all in kΩ except vcc, beta, vbe)
MODE_FIELDS = {
    "divider": ("vcc", "r1", "r2", "rc", "re", "beta", "vbe"),
    "fixed": ("vcc", "rb", "rc", "beta", "vbe"),
    "emitter": ("vcc", "rb", "re", "rc", "beta", "vbe"),
}

# SPICE analysis modes need the extra CE amplifier parts
SPICE_FIELDS = ("rl", "cin", "cout", "amplitude", "frequency")

POSITIVE_FIELDS = ("vcc", "r1", "r2", "rc", "re", "rb", "beta", "rl")


def parse_form(form):
    """Return ``(values, errors)`` for a submitted form.

    ``values`` holds only the fields that survived validation. ``errors`` maps
    a field name to a message the user can act on.
    """
    mode = (form.get("mode") or "divider").strip()
    if mode not in MODE_FIELDS:
        return {}, {"mode": "โหมดวงจรไม่ถูกต้อง"}

    analysis = (form.get("analysis") or "analytical").strip()
    if analysis not in ANALYSIS_LABELS:
        return {}, {"analysis": "โหมดวิเคราะห์ไม่ถูกต้อง"}

    values = {"mode": mode, "analysis": analysis}
    errors = {}

    required = MODE_FIELDS[mode]
    if analysis.startswith("spice_"):
        required = required + SPICE_FIELDS

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

    if analysis.startswith("spice_"):
        if "cin" in values and values["cin"] <= 0:
            errors["cin"] = "ต้องมากกว่า 0"
        if "cout" in values and values["cout"] <= 0:
            errors["cout"] = "ต้องมากกว่า 0"
        if "amplitude" in values and values["amplitude"] <= 0:
            errors["amplitude"] = "ต้องมากกว่า 0"
        if "frequency" in values and values["frequency"] <= 0:
            errors["frequency"] = "ต้องมากกว่า 0"

    for name in errors:
        values.pop(name, None)

    return values, errors


@app.get("/")
def index():
    """Render the input form filled with the lab's sample values."""
    mode = request.args.get("mode", "divider")
    if mode not in MODE_FIELDS:
        mode = "divider"
    analysis = request.args.get("analysis", "analytical")
    if analysis not in ANALYSIS_LABELS:
        analysis = "analytical"
    form = dict(DEFAULTS)
    form["mode"] = mode
    form["analysis"] = analysis
    return render_template(
        "index.html",
        form=form,
        errors={},
        result=None,
        analysis=analysis,
        labels=FIELD_LABELS,
        modes=MODE_FIELDS,
        mode_labels=MODE_LABELS,
        selected_mode=mode,
        selected_analysis=analysis,
        analysis_labels=ANALYSIS_LABELS,
    )


SPICE_ANALYSIS_KEYS = {
    "spice_op": "op",
    "spice_ac": "ac",
    "spice_tran": "tran",
}


def _compute_bias(mode: str, values: dict):
    """Run the analytical DC bias calculation for the selected mode."""
    if mode == "divider":
        return dc_bias.divider_bias(
            vcc=values["vcc"],
            r1_k=values["r1"],
            r2_k=values["r2"],
            rc_k=values["rc"],
            re_k=values["re"],
            beta=values["beta"],
            vbe=values["vbe"],
        )
    if mode == "fixed":
        return dc_bias.fixed_bias(
            vcc=values["vcc"],
            rb_k=values["rb"],
            rc_k=values["rc"],
            beta=values["beta"],
            vbe=values["vbe"],
        )
    return dc_bias.emitter_bias(
        vcc=values["vcc"],
        rb_k=values["rb"],
        re_k=values["re"],
        rc_k=values["rc"],
        beta=values["beta"],
        vbe=values["vbe"],
    )


def _spice_params(values: dict) -> dict:
    """Map validated form values onto the ngspice parameter boundary."""
    return {
        "vcc": values["vcc"],
        "r1_k": values["r1"],
        "r2_k": values["r2"],
        "rc_k": values["rc"],
        "re_k": values["re"],
        "rl_k": values["rl"],
        "cin_f": values["cin"],
        "cout_f": values["cout"],
        "amplitude_v": values["amplitude"],
        "frequency_hz": values["frequency"],
        "vbe": values["vbe"],
    }


@app.post("/calculate")
def calculate():
    """Compute the DC operating point and render it alongside the form."""
    values, errors = parse_form(request.form)

    mode = values.get("mode") or "divider"
    analysis = values.get("analysis") or "analytical"

    if errors:
        return render_template(
            "index.html",
            form=request.form,
            errors=errors,
            result=None,
            analysis=analysis,
            labels=FIELD_LABELS,
            modes=MODE_FIELDS,
            mode_labels=MODE_LABELS,
            selected_mode=mode,
            selected_analysis=analysis,
            analysis_labels=ANALYSIS_LABELS,
        )

    mode = values["mode"]
    try:
        if analysis == "analytical":
            result = _compute_bias(mode, values)
        else:
            spice = spice_engine.simulate(
                _spice_params(values), SPICE_ANALYSIS_KEYS[analysis]
            )
    except ValueError as exc:
        return render_template(
            "index.html",
            form=request.form,
            errors={},
            form_error=str(exc),
            result=None,
            analysis=analysis,
            labels=FIELD_LABELS,
            modes=MODE_FIELDS,
            mode_labels=MODE_LABELS,
            selected_mode=mode,
            analysis_labels=ANALYSIS_LABELS,
        )

    if analysis != "analytical":
        return render_template(
            "index.html",
            form=request.form,
            errors={},
            result=None,
            spice=spice,
            analysis=analysis,
            labels=FIELD_LABELS,
            modes=MODE_FIELDS,
            mode_labels=MODE_LABELS,
            selected_mode=mode,
            selected_analysis=analysis,
            analysis_labels=ANALYSIS_LABELS,
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
        selected_analysis=analysis,
        analysis_labels=ANALYSIS_LABELS,
    )
