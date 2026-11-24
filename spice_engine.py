"""ngspice adapter for BJT Common-Emitter amplifier simulation.

Owns the interface to the external ngspice binary: building netlists,
running the solver via subprocess, and parsing results with units.
Knows nothing about Flask or HTML.

Units at this boundary:

* voltages in volts
* resistances in kilohms (suffix ``_k``) coming in, converted to ohms in netlist
* capacitances in farads
* source amplitude in volts peak, frequency in hertz
"""

import math
import os
import re
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


#: Path to the ngspice executable. Override via NGSPICE_EXE env var.
NGSPICE_EXE = os.environ.get("NGSPICE_EXE", r"C:\msys64\ucrt64\bin\ngspice.exe")

#: Default reference circuit values (Lab 04 baseline fixture).
DEFAULTS = {
    "vcc": 12.0,
    "r1_k": 100.0,
    "r2_k": 22.0,
    "rc_k": 2.2,
    "re_k": 1.0,
    "rl_k": 10.0,
    "cin_f": 10e-6,
    "cout_f": 10e-6,
    "amplitude_v": 10e-3,
    "frequency_hz": 1e3,
}

ANALYSES = ("op", "ac", "tran")


@dataclass
class SpiceResult:
    """Result from one ngspice analysis run."""

    analysis: str
    success: bool
    engine: str = "ngspice"
    engine_version: str | None = None
    netlist: str | None = None
    log: str | None = None
    raw: bytes | None = None
    error: str | None = None
    data: dict[str, Any] | None = None


def _ngspice_version() -> str | None:
    """Return ngspice version string, or None if not available."""
    try:
        proc = subprocess.run(
            [NGSPICE_EXE, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout.strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def _version_from_raw(raw_bytes: bytes | None) -> str | None:
    """Read the solver version from the raw file header.

    ``ngspice --version`` prints nothing on the MSYS2 build, but every raw
    file carries a ``Command: ngspice-47, Build ...`` line.
    """
    if not raw_bytes:
        return None
    header = raw_bytes[:1000].decode("latin-1", errors="replace")
    match = re.search(r"Command:\s*(ngspice-[\w.]+)", header, re.IGNORECASE)
    return match.group(1) if match else None


def build_netlist(params: dict, analysis: str) -> str:
    """Build a CE voltage-divider netlist for the given analysis."""
    if analysis not in ANALYSES:
        raise ValueError(f"unsupported analysis: {analysis}")

    vcc = params["vcc"]
    r1 = params["r1_k"]
    r2 = params["r2_k"]
    rc = params["rc_k"]
    re_ = params["re_k"]
    rl = params["rl_k"]
    cin = params["cin_f"]
    cout = params["cout_f"]
    amplitude = params["amplitude_v"]
    freq = params["frequency_hz"]
    vbe = params.get("vbe", 0.7)

    lines = [
        "* CE Voltage-Divider Amplifier - Lab 04",
        "* Reference circuit (single NPN, unbypassed RE)",
        f"V1 VCC 0 DC {vcc:g}",
        f"R1 VCC BASE {r1:g}k",
        f"R2 BASE 0 {r2:g}k",
        f"RC VCC COLLECTOR {rc:g}k",
        f"RE EMITTER 0 {re_:g}k",
        f"RL OUTPUT 0 {rl:g}k",
        f"CIN INPUT BASE {cin:g}",
        f"COUT COLLECTOR OUTPUT {cout:g}",
    ]

    if analysis == "ac":
        lines.append(f"VIN INPUT 0 AC {amplitude:g}")
    elif analysis == "tran":
        lines.append(f"VIN INPUT 0 SIN(0 {amplitude:g} {freq:g})")
    else:
        lines.append("VIN INPUT 0 DC 0")

    lines.extend(
        [
            "Q1 COLLECTOR BASE EMITTER NPN",
            ".model NPN npn (IS=1e-14 BF=100 VAF=100)",
        ]
    )

    if analysis == "op":
        lines.append(".op")
    elif analysis == "ac":
        f_low = freq / 1000.0
        f_high = freq * 1000.0
        lines.append(f".ac dec 50 {f_low:g} {f_high:.0f}")
        lines.append(".print ac vm(COLLECTOR) vp(COLLECTOR)")
    else:
        # 100 samples per cycle, 10 cycles: avoids aliasing the input sine.
        tstep = 1.0 / (freq * 100.0)
        tstop = 10.0 / freq
        lines.append(f".ic V(BASE) = {vbe:g}")
        lines.append(f".tran {tstep:g} {tstop:g}")
        lines.append(".print tran v(input) v(collector)")

    lines.append(".end")
    return "\n".join(lines) + "\n"


def run_ngspice(netlist: str, analysis: str, workdir: str | None = None) -> SpiceResult:
    """Run ngspice on the given netlist and return a SpiceResult.

    Uses subprocess.run with a list of arguments (no shell=True), a timeout,
    and a separate working directory per run, per Lab 04 requirements.
    """
    if workdir is None:
        workdir = tempfile.mkdtemp(prefix="spice_")

    workdir_path = Path(workdir)
    workdir_path.mkdir(parents=True, exist_ok=True)

    netlist_path = workdir_path / "circuit.cir"
    log_path = workdir_path / "run.log"
    raw_path = workdir_path / "run.raw"

    netlist_path.write_text(netlist, encoding="utf-8")

    try:
        proc = subprocess.run(
            [
                NGSPICE_EXE,
                "-b",
                "-o",
                str(log_path),
                "-r",
                str(raw_path),
                str(netlist_path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(workdir_path),
        )
    except FileNotFoundError:
        return SpiceResult(
            analysis=analysis,
            success=False,
            engine="ngspice",
            netlist=netlist,
            error=f"ngspice executable not found at {NGSPICE_EXE}",
        )
    except subprocess.TimeoutExpired as exc:
        return SpiceResult(
            analysis=analysis,
            success=False,
            engine="ngspice",
            netlist=netlist,
            log=exc.stdout or "",
            error="ngspice run timed out",
        )

    log_text = (
        log_path.read_text(encoding="utf-8", errors="replace")
        if log_path.exists()
        else ""
    )
    raw_bytes = raw_path.read_bytes() if raw_path.exists() else None
    stdout_text = proc.stdout or ""

    combined = log_text + ("\n--- stdout ---\n" + stdout_text if stdout_text else "")
    success = proc.returncode == 0 and "No. of Data Rows" in combined

    return SpiceResult(
        analysis=analysis,
        success=success,
        engine="ngspice",
        engine_version=_ngspice_version() or _version_from_raw(raw_bytes),
        netlist=netlist,
        log=combined,
        raw=raw_bytes,
        error=None if success else (stdout_text or log_text or "unknown error"),
    )


#: Voltage node table line: lowercase node name followed by a numeric value.
_NODE_PLAIN_LINE_RE = re.compile("^([a-z_][a-z0-9_]*)[^0-9.eE+-]+([0-9.eE+-]+)$")
#: Voltage reference line: V(node) followed by a numeric value.
_NODE_VOLTAGE_RE = re.compile("V([^)]+)[^0-9.eE+-]+([0-9.eE+-]+)")
#: Source branch current line: v<number>#branch followed by a numeric value.
_SOURCE_CURRENT_RE = re.compile("v([0-9]+)#[^0-9.eE+-]+([0-9.eE+-]+)")
#: BJT device block: device / ic / ib / ie / vbe values.
_BJT_RE = re.compile(
    "BJT: Bipolar Junction Transistor.*?device[ ]+([A-Za-z][A-Za-z0-9]*)"
    ".*?ic[^0-9.eE+-]*([0-9.eE+-]+)"
    ".*?ib[^0-9.eE+-]*([0-9.eE+-]+)"
    ".*?ie[^0-9.eE+-]*([0-9.eE+-]+)"
    ".*?vbe[^0-9.eE+-]*([0-9.eE+-]+)",
    re.DOTALL,
)
#: Data row line: index, then three numeric columns.
_POINT_RE = re.compile(
    "^([0-9]+)[^0-9.eE+-]+([0-9.eE+-]+)[^0-9.eE+-]+([0-9.eE+-]+)[^0-9.eE+-]+([0-9.eE+-]+)"
)

#: Node names the reference netlist uses (lowercased for matching).
_KNOWN_NODES = {"base", "collector", "emitter", "vcc", "input", "output"}


def parse_raw(raw_bytes: bytes) -> dict[str, Any]:
    """Parse an ngspice binary raw file into variable names and values.

    ngspice writes a text header followed by a ``Binary:`` marker and
    64-bit values. Complex analyses store a (real, imaginary) pair per
    variable; real analyses store a single value.
    """
    marker = b"Binary:"
    split_at = raw_bytes.find(marker)
    if split_at < 0:
        raise ValueError("raw file has no binary marker")
    header = raw_bytes[:split_at].decode("latin-1")
    payload = raw_bytes[split_at + len(marker) :].lstrip(b"\r\n")

    variables: list[str] = []
    meta: dict[str, str] = {}
    in_variables = False
    for line in header.splitlines():
        if line.startswith("Variables:"):
            in_variables = True
            continue
        if in_variables:
            columns = line.split()
            if len(columns) >= 3 and columns[0].isdigit():
                variables.append(columns[1])
            continue
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()

    try:
        variable_count = int(meta["No. Variables"])
        point_count = int(meta["No. Points"])
    except KeyError as exc:
        raise ValueError(f"raw file header missing {exc}") from exc
    if len(variables) != variable_count:
        raise ValueError("raw file variable count mismatch")

    is_complex = "complex" in meta.get("Flags", "").split()
    stride = variable_count * (2 if is_complex else 1)
    needed = point_count * stride
    try:
        numbers = struct.unpack("<" + "d" * needed, payload[: needed * 8])
    except struct.error as exc:
        raise ValueError("raw file payload is truncated") from exc

    rows = []
    for point in range(point_count):
        base = point * stride
        row = []
        for index in range(variable_count):
            if is_complex:
                row.append(
                    complex(numbers[base + 2 * index], numbers[base + 2 * index + 1])
                )
            else:
                row.append(numbers[base + index])
        rows.append(row)

    return {
        "variables": variables,
        "points": rows,
        "flags": meta.get("Flags", ""),
        "plotname": meta.get("Plotname", ""),
    }


def _raw_values(parsed: dict[str, Any], name: str) -> list:
    """Return one named column from parsed raw data (case-insensitive)."""
    names = [item.lower() for item in parsed["variables"]]
    index = names.index(name.lower())
    return [row[index] for row in parsed["points"]]


def _phase_deg(value) -> float:
    """Phase of a real or complex raw value, in degrees."""
    if isinstance(value, complex):
        return math.degrees(math.atan2(value.imag, value.real))
    return 0.0


def parse_op(text: str, raw: bytes | None = None) -> dict[str, Any]:
    """Parse .op output text into node voltages and BJT device data."""
    data: dict[str, Any] = {"type": "dc_operating_point"}

    voltages: dict[str, float] = {}
    for line in text.splitlines():
        stripped = line.strip()
        match = _NODE_PLAIN_LINE_RE.match(stripped)
        if match:
            node = match.group(1).lower()
            value = float(match.group(2))
            if node in _KNOWN_NODES:
                voltages[node] = value
    for match in _NODE_VOLTAGE_RE.finditer(text):
        node = match.group(1).lower()
        if node not in _KNOWN_NODES:
            continue
        value = float(match.group(2))
        voltages[node] = value
    data["node_voltages"] = voltages

    for match in _SOURCE_CURRENT_RE.finditer(text):
        source = f"V{match.group(1)}"
        data[f"i_{source.lower()}"] = float(match.group(2))

    bjt_match = _BJT_RE.search(text)
    if bjt_match:
        data["bjt_device"] = bjt_match.group(1)
        data["ic"] = float(bjt_match.group(2))
        data["ib"] = float(bjt_match.group(3))
        data["ie"] = float(bjt_match.group(4))
        data["vbe"] = float(bjt_match.group(5))

    if raw:
        parsed = parse_raw(raw)
        for index, name in enumerate(parsed["variables"]):
            lowered = name.lower()
            value = parsed["points"][0][index]
            number = value.real if isinstance(value, complex) else float(value)
            if lowered.startswith("v("):
                voltages[lowered[2:-1]] = number
            elif lowered.startswith("i(v"):
                data[f"i_{lowered[2:-1]}"] = number
        data["node_voltages"] = voltages

    if "collector" in voltages and "emitter" in voltages:
        data["vce"] = voltages["collector"] - voltages["emitter"]

    return data


def parse_ac(text: str, raw: bytes | None = None) -> dict[str, Any]:
    """Parse .ac output into frequency/gain/phase points (raw file preferred)."""
    data: dict[str, Any] = {"type": "ac_frequency_response", "points": []}
    if raw:
        parsed = parse_raw(raw)
        for frequency, vin, vout in zip(
            _raw_values(parsed, "frequency"),
            _raw_values(parsed, "v(input)"),
            _raw_values(parsed, "v(collector)"),
        ):
            magnitude = abs(vin)
            data["points"].append(
                {
                    "frequency_hz": float(frequency.real if isinstance(frequency, complex) else frequency),
                    "gain_magnitude": abs(vout) / magnitude if magnitude else 0.0,
                    "phase_deg": _phase_deg(vout) - _phase_deg(vin),
                }
            )
        return data
    for line in text.splitlines():
        match = _POINT_RE.match(line.strip())
        if match:
            try:
                data["points"].append(
                    {
                        "frequency_hz": float(match.group(2)),
                        "gain_magnitude": float(match.group(3)),
                        "phase_deg": float(match.group(4)),
                    }
                )
            except ValueError:
                continue
    return data


def parse_tran(text: str, raw: bytes | None = None) -> dict[str, Any]:
    """Parse .tran output into time/input/output points (raw file preferred)."""
    data: dict[str, Any] = {"type": "transient_response", "points": []}
    if raw:
        parsed = parse_raw(raw)
        for time, vin, vout in zip(
            _raw_values(parsed, "time"),
            _raw_values(parsed, "v(input)"),
            _raw_values(parsed, "v(collector)"),
        ):
            data["points"].append(
                {
                    "time_s": float(time.real if isinstance(time, complex) else time),
                    "vin_v": vin.real if isinstance(vin, complex) else float(vin),
                    "vout_v": vout.real if isinstance(vout, complex) else float(vout),
                }
            )
        return data
    for line in text.splitlines():
        match = _POINT_RE.match(line.strip())
        if match:
            try:
                data["points"].append(
                    {
                        "time_s": float(match.group(2)),
                        "vin_v": float(match.group(3)),
                        "vout_v": float(match.group(4)),
                    }
                )
            except ValueError:
                continue
    return data


_PARSERS = {
    "op": parse_op,
    "ac": parse_ac,
    "tran": parse_tran,
}


def simulate(params: dict, analysis: str, workdir: str | None = None) -> SpiceResult:
    """Run one ngspice analysis and return a parsed SpiceResult.

    This is the entry point used by app.py: build netlist -> run ngspice ->
    parse results with units.
    """
    if analysis not in ANALYSES:
        return SpiceResult(
            analysis=analysis,
            success=False,
            engine="ngspice",
            error=f"unsupported analysis: {analysis}",
        )

    netlist = build_netlist(params, analysis)
    result = run_ngspice(netlist, analysis, workdir=workdir)

    if result.success and (result.log or result.raw):
        parser = _PARSERS[analysis]
        try:
            result.data = parser(result.log or "", raw=result.raw)
        except Exception as exc:  # noqa: BLE001
            result.success = False
            result.data = None
            result.error = f"parse error: {exc}"

    return result
