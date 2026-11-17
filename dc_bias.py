"""DC bias calculations for an NPN common-emitter stage.

Model: forward-active approximation with a constant current gain ``beta``
and a constant base-emitter drop ``vbe``. Supports three bias circuits:

* Voltage Divider Bias (loading-aware: base current loads the divider)
* Fixed Bias
* Emitter Bias (single supply)

Units at this boundary:

* ``vcc`` in volts
* every resistance parameter in **kilohms** (suffix ``_k``)
* ``rth`` returned in **kilohms** (None for Fixed and Emitter bias)
* ``ib``, ``ic``, ``ie`` returned in **amperes**

Flask, HTML and formatting must never appear in this module.
"""

from dataclasses import dataclass

KOHM = 1000.0

#: Below this collector-emitter voltage the forward-active model is not valid.
VCE_SATURATION = 0.3

#: Between VCE_SATURATION and this value the point is active but close to the edge.
VCE_NEAR_SATURATION = 0.7

#: At or below this VCE, warn that the Forward-Active model may not be valid.
VCE_MODEL_LIMIT = 0.2

_CUTOFF_WARNING = (
    "แรงดันเบสจากตัวแบ่ง (VTH) ไม่สูงพอที่จะไบอัสตรงรอยต่อเบส-อีมิเตอร์ "
    "ทรานซิสเตอร์จึงอยู่ในช่วง cutoff — แบบจำลอง Forward-Active ใช้กับจุดนี้ไม่ได้"
)

_SATURATION_WARNING = (
    "VCE ต่ำกว่า 0.3 V ทรานซิสเตอร์อยู่ในช่วงอิ่มตัว (saturation) "
    "ค่าที่คำนวณได้จากแบบจำลอง Forward-Active ไม่น่าเชื่อถือ"
)

_NEAR_SATURATION_WARNING = (
    "VCE อยู่ใกล้ช่วงอิ่มตัว (ต่ำกว่า 0.7 V) ผลที่ได้อาจคลาดเคลื่อนจากวงจรจริง"
)

_MODEL_LIMIT_WARNING = (
    "VCE ต่ำกว่าหรือเท่ากับ 0.2 V แบบจำลอง Forward-Active อาจใช้ไม่ได้กับจุดนี้"
)


@dataclass(frozen=True)
class BiasResult:
    """DC operating point of the stage, in volts and amperes.

    ``vth`` and ``rth`` are only meaningful for Voltage Divider bias;
    they are ``None`` for Fixed and Emitter bias.
    """

    vth: float | None
    rth: float | None
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warnings: tuple[str, ...]


def bias_network(vcc: float, r1_k: float, r2_k: float) -> tuple[float, float]:
    """Return ``(vth in volts, rth in kilohms)`` for the divider network."""
    vth = vcc * r2_k / (r1_k + r2_k)
    rth_k = r1_k * r2_k / (r1_k + r2_k)
    return vth, rth_k


def _classify(
    vce: float, ib: float, warnings_extra: tuple[str, ...] = ()
) -> tuple[str, tuple[str, ...]]:
    """Classify region and build warnings from vce and ib."""
    warnings = list(warnings_extra)

    if ib <= 0:
        warnings.append(
            "กระแสเบสคำนวณได้ติดลบหรือเป็นศูนย์ แบบจำลอง Forward-Active "
            "ใช้ไม่ได้ — ตรวจสอบอินพุตหรือวงจรอาจอยู่ในช่วง cutoff"
        )

    if vce < VCE_SATURATION:
        region = "SATURATION"
        warnings.append(_SATURATION_WARNING)
    elif vce < VCE_NEAR_SATURATION:
        region = "ACTIVE"
        warnings.append(_NEAR_SATURATION_WARNING)
    elif vce <= VCE_MODEL_LIMIT:
        region = "ACTIVE"
        warnings.append(_MODEL_LIMIT_WARNING)
    else:
        region = "ACTIVE"

    return region, tuple(warnings)


def divider_bias(
    vcc: float,
    r1_k: float,
    r2_k: float,
    rc_k: float,
    re_k: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Voltage Divider Bias with base-current loading (per Lab 03 spec).

    IB = (VTH − VBE) / [RTH + (β + 1)RE]
    """
    _require_positive("vcc", vcc)
    _require_positive("r1_k", r1_k)
    _require_positive("r2_k", r2_k)
    _require_positive("rc_k", rc_k)
    _require_positive("re_k", re_k)
    _require_positive("beta", beta)
    _require_positive("vbe", vbe)
    if vbe >= vcc:
        raise ValueError("vbe must be smaller than vcc")

    vth, rth_k = bias_network(vcc, r1_k, r2_k)

    if vth <= vbe:
        return BiasResult(
            vth=vth,
            rth=rth_k,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vb=vth,
            ve=0.0,
            vc=vcc,
            vce=vcc,
            region="CUTOFF",
            warnings=(_CUTOFF_WARNING,),
        )

    ib = (vth - vbe) / (rth_k * KOHM + (beta + 1.0) * re_k * KOHM)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re_k * KOHM
    vb = ve + vbe
    vc = vcc - ic * rc_k * KOHM
    vce = vc - ve

    region, warnings = _classify(vce, ib)

    return BiasResult(
        vth=vth,
        rth=rth_k,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )


def fixed_bias(
    vcc: float,
    rb_k: float,
    rc_k: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Fixed Bias.

    IB = (VCC − VBE) / RB,  VE = 0,  VB = VBE
    """
    _require_positive("vcc", vcc)
    _require_positive("rb_k", rb_k)
    _require_positive("rc_k", rc_k)
    _require_positive("beta", beta)
    _require_positive("vbe", vbe)
    if vbe >= vcc:
        raise ValueError("vbe must be smaller than vcc")

    ib = (vcc - vbe) / (rb_k * KOHM)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = 0.0
    vb = vbe
    vc = vcc - ic * rc_k * KOHM
    vce = vc - ve

    region, warnings = _classify(vce, ib)

    return BiasResult(
        vth=None,
        rth=None,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )


def emitter_bias(
    vcc: float,
    rb_k: float,
    re_k: float,
    rc_k: float,
    beta: float,
    vbe: float,
) -> BiasResult:
    """Emitter Bias (single supply).

    IB = (VCC − VBE) / [RB + (β + 1)RE]
    """
    _require_positive("vcc", vcc)
    _require_positive("rb_k", rb_k)
    _require_positive("re_k", re_k)
    _require_positive("rc_k", rc_k)
    _require_positive("beta", beta)
    _require_positive("vbe", vbe)
    if vbe >= vcc:
        raise ValueError("vbe must be smaller than vcc")

    ib = (vcc - vbe) / (rb_k * KOHM + (beta + 1.0) * re_k * KOHM)
    ic = beta * ib
    ie = (beta + 1.0) * ib
    ve = ie * re_k * KOHM
    vb = ve + vbe
    vc = vcc - ic * rc_k * KOHM
    vce = vc - ve

    region, warnings = _classify(vce, ib)

    return BiasResult(
        vth=None,
        rth=None,
        ib=ib,
        ic=ic,
        ie=ie,
        vb=vb,
        ve=ve,
        vc=vc,
        vce=vce,
        region=region,
        warnings=warnings,
    )


def _require_positive(name: str, value: float) -> None:
    if not value > 0:
        raise ValueError(f"{name} must be greater than zero")
