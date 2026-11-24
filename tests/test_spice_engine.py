"""Unit tests for the ngspice adapter (spice_engine).

Imports only spice_engine, per AGENTS.md. Uses unittest.mock so tests do not
require the ngspice binary to be present.
"""

from __future__ import annotations

import math
import struct
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import spice_engine


class TestBuildNetlist(unittest.TestCase):
    """Netlist must contain the right analysis directive for each mode."""

    def setUp(self):
        self.params = {
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

    def test_op_netlist_contains_op_directive(self):
        netlist = spice_engine.build_netlist(self.params, "op")
        self.assertIn(".op", netlist)
        # ngspice on Windows does not support .print dc together with .op,
        # so the op netlist must not contain it.
        self.assertNotIn(".print dc", netlist)

    def test_ac_netlist_contains_ac_directive(self):
        netlist = spice_engine.build_netlist(self.params, "ac")
        self.assertIn(".ac", netlist)
        self.assertIn(".print ac", netlist)

    def test_tran_netlist_contains_tran_directive(self):
        netlist = spice_engine.build_netlist(self.params, "tran")
        self.assertIn(".tran", netlist)
        self.assertIn(".print tran", netlist)

    def test_tran_netlist_prints_input_and_collector(self):
        netlist = spice_engine.build_netlist(self.params, "tran")
        # Column layout must be: Index, time, v(input), v(collector) so that
        # parse_tran can map (time, vin, vout) without guessing.
        self.assertIn(".print tran v(input) v(collector)", netlist)

    def test_unsupported_analysis_raises(self):
        with self.assertRaises(ValueError):
            spice_engine.build_netlist(self.params, "noise")

    def test_netlist_includes_all_components(self):
        netlist = spice_engine.build_netlist(self.params, "op")
        for token in ("V1", "R1", "R2", "RC", "RE", "RL", "CIN", "COUT", "Q1", ".model NPN"):
            self.assertIn(token, netlist)

    def test_ac_netlist_includes_source(self):
        netlist = spice_engine.build_netlist(self.params, "ac")
        self.assertIn("VIN", netlist)

    def test_tran_timing_derived_from_frequency(self):
        netlist = spice_engine.build_netlist(self.params, "tran")
        # f = 1 kHz -> tstep = 10 us (100 samples/cycle), 10 cycles = 10 ms
        self.assertIn(".tran 1e-05 0.01", netlist)

    def test_tran_timing_follows_other_frequencies(self):
        params = dict(self.params, frequency_hz=500.0)
        netlist = spice_engine.build_netlist(params, "tran")
        self.assertIn(".tran 2e-05 0.02", netlist)


class TestRunNgspice(unittest.TestCase):
    """subprocess invocation must be safe: list args, no shell, timeout, cwd."""

    def setUp(self):
        self.netlist = "* test\n.end\n"
        self.fake_success = MagicMock()
        self.fake_success.returncode = 0
        self.fake_success.stdout = ""
        self.fake_success.stderr = ""

    @patch("spice_engine.subprocess.run")
    def test_calls_ngspice_with_list_args_not_shell(self, mock_run):
        mock_run.return_value = self.fake_success
        with patch("pathlib.Path.write_text"), patch("pathlib.Path.read_text", return_value=""):
            with patch.object(spice_engine, "_ngspice_version", return_value="ngspice 47"):
                spice_engine.run_ngspice(self.netlist, "op", workdir="/tmp/x")
        self.assertTrue(mock_run.called)
        call_args = mock_run.call_args
        args = call_args[0][0]
        self.assertIsInstance(args, list)
        self.assertEqual(args[0], spice_engine.NGSPICE_EXE)
        self.assertIn("-b", args)
        self.assertIn("-o", args)
        self.assertFalse(call_args[1].get("shell", False))

    @patch("spice_engine.subprocess.run")
    def test_batch_invocation_requests_raw_output_file(self, mock_run):
        mock_run.return_value = self.fake_success
        with patch("pathlib.Path.write_text"), patch("pathlib.Path.read_text", return_value=""):
            with patch.object(spice_engine, "_ngspice_version", return_value="ngspice 47"):
                spice_engine.run_ngspice(self.netlist, "op", workdir="/tmp/x")
        args = mock_run.call_args[0][0]
        self.assertIn("-r", args)
        self.assertTrue(any(str(arg).endswith("run.raw") for arg in args))

    @patch("spice_engine.subprocess.run")
    def test_uses_separate_working_directory(self, mock_run):
        mock_run.return_value = self.fake_success
        with patch("pathlib.Path.write_text"), patch("pathlib.Path.read_text", return_value=""):
            with patch.object(spice_engine, "_ngspice_version", return_value="ngspice 47"):
                spice_engine.run_ngspice(self.netlist, "op", workdir="/tmp/run1")
        self.assertEqual(Path(mock_run.call_args[1]["cwd"]), Path("/tmp/run1"))

    @patch("spice_engine.subprocess.run")
    def test_timeout_is_enforced(self, mock_run):
        mock_run.return_value = self.fake_success
        with patch("pathlib.Path.write_text"), patch("pathlib.Path.read_text", return_value=""):
            with patch.object(spice_engine, "_ngspice_version", return_value="ngspice 47"):
                spice_engine.run_ngspice(self.netlist, "op", workdir="/tmp/x")
        kwargs = mock_run.call_args[1]
        self.assertIn("timeout", kwargs)
        self.assertGreater(kwargs["timeout"], 0)

    @patch("spice_engine.subprocess.run")
    def test_engine_version_is_read_from_raw_header(self, mock_run):
        mock_run.return_value = self.fake_success
        raw = (
            b"Title: test\n"
            b"Command: ngspice-47, Build Mon Sep  7 15:42:04 UTC 2026\n"
            b"Variables:\n\t0\ttime\ttime\nBinary:\n"
        )
        with patch("pathlib.Path.write_text"), \
                patch("pathlib.Path.exists", return_value=True), \
                patch("pathlib.Path.read_text", return_value="No. of Data Rows : 1"), \
                patch("pathlib.Path.read_bytes", return_value=raw), \
                patch.object(spice_engine, "_ngspice_version", return_value=None):
            result = spice_engine.run_ngspice(self.netlist, "op", workdir="/tmp/x")
        self.assertEqual(result.engine_version, "ngspice-47")

    @patch("spice_engine.subprocess.run")
    def test_missing_executable_returns_failure_not_crash(self, mock_run):
        mock_run.side_effect = FileNotFoundError("ngspice not found")
        result = spice_engine.run_ngspice(self.netlist, "op", workdir="/tmp/x")
        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertIn("ngspice", result.error.lower())


class TestParseOp(unittest.TestCase):
    """.op output must yield node voltages and BJT device data."""

    def test_parse_op_extracts_node_voltages(self):
        text = """
	Node                                  Voltage
	----                                  -------
	base                             1.949112e+00
	collector                        9.189410e+00
	emitter                          1.289454e+00
"""
        data = spice_engine.parse_op(text)
        self.assertAlmostEqual(data["node_voltages"]["base"], 1.949112)
        self.assertAlmostEqual(data["node_voltages"]["collector"], 9.189410)
        self.assertAlmostEqual(data["node_voltages"]["emitter"], 1.289454)
        self.assertAlmostEqual(data["vce"], 9.189410 - 1.289454, places=4)

    def test_parse_op_extracts_bjt_device(self):
        text = """
 BJT: Bipolar Junction Transistor
     device                    q1
      model                   npn
         ic            0.00127819
         ib            1.1919e-05
         ie           -0.00129011
         vbe              0.659658
"""
        data = spice_engine.parse_op(text)
        self.assertEqual(data["bjt_device"], "q1")
        self.assertAlmostEqual(data["ic"], 0.00127819)
        self.assertAlmostEqual(data["ib"], 1.1919e-05)
        self.assertAlmostEqual(data["vbe"], 0.659658)


class TestParseRaw(unittest.TestCase):
    """ngspice -r writes binary raw; it is the data source when requested."""

    @staticmethod
    def raw_bytes(variables, rows, complex_values=False):
        flags = "complex" if complex_values else "real"
        header = (
            "Title: test\n"
            f"Flags: {flags}\n"
            f"No. Variables: {len(variables)}\n"
            f"No. Points: {len(rows)}\n"
            "Variables:\n"
        )
        for index, name in enumerate(variables):
            header += f"\t{index}\t{name}\tvoltage\n"
        header += "Binary:\n"
        numbers = []
        for row in rows:
            for value in row:
                if complex_values:
                    numbers.extend([value.real, value.imag])
                else:
                    numbers.append(float(value))
        return header.encode("latin-1") + struct.pack(
            "<" + "d" * len(numbers), *numbers
        )

    def test_parse_raw_reads_real_points(self):
        raw = self.raw_bytes(["time", "v(input)"], [[0.0, 0.01], [1e-5, 0.02]])
        parsed = spice_engine.parse_raw(raw)
        self.assertEqual(parsed["variables"], ["time", "v(input)"])
        self.assertEqual(len(parsed["points"]), 2)
        self.assertAlmostEqual(parsed["points"][1][1], 0.02)

    def test_parse_raw_reads_complex_points(self):
        raw = self.raw_bytes(
            ["frequency", "v(collector)"], [[1.0, 0.02 + 0.5j]], complex_values=True
        )
        parsed = spice_engine.parse_raw(raw)
        self.assertEqual(parsed["points"][0][1], 0.02 + 0.5j)

    def test_parse_op_uses_raw_node_voltages(self):
        raw = self.raw_bytes(
            ["v(base)", "v(collector)", "v(emitter)"],
            [[1.9, 9.2, 1.3]],
        )
        data = spice_engine.parse_op("", raw=raw)
        self.assertAlmostEqual(data["node_voltages"]["base"], 1.9)
        self.assertAlmostEqual(data["vce"], 7.9)

    def test_parse_ac_uses_raw_complex_values(self):
        raw = self.raw_bytes(
            ["frequency", "v(input)", "v(collector)"],
            [[1.0, 0.01 + 0j, 0.02 + 0j]],
            complex_values=True,
        )
        data = spice_engine.parse_ac("", raw=raw)
        self.assertEqual(len(data["points"]), 1)
        self.assertAlmostEqual(data["points"][0]["frequency_hz"], 1.0)
        self.assertAlmostEqual(data["points"][0]["gain_magnitude"], 2.0)
        self.assertAlmostEqual(data["points"][0]["phase_deg"], 0.0)

    def test_parse_tran_uses_raw_waveforms(self):
        raw = self.raw_bytes(
            ["time", "v(input)", "v(collector)"],
            [[0.0, 0.0, 11.7], [1e-5, 0.001, 11.6]],
        )
        data = spice_engine.parse_tran("", raw=raw)
        self.assertEqual(len(data["points"]), 2)
        self.assertAlmostEqual(data["points"][1]["time_s"], 1e-5)
        self.assertAlmostEqual(data["points"][1]["vin_v"], 0.001)
        self.assertAlmostEqual(data["points"][1]["vout_v"], 11.6)


class TestSimulateIntegration(unittest.TestCase):
    """End-to-end simulate() wires build + run + parse together."""

    @patch("spice_engine.run_ngspice")
    def test_simulate_op_parses_result(self, mock_run):
        mock_run.return_value = spice_engine.SpiceResult(
            analysis="op",
            success=True,
            engine="ngspice",
            netlist=".op\n.end",
            log="V(BASE) 1.949\n",
        )
        params = {
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
        result = spice_engine.simulate(params, "op")
        self.assertTrue(result.success)
        mock_run.assert_called_once()
        self.assertIn("op", mock_run.call_args[0][0])

    @patch("spice_engine.run_ngspice")
    def test_simulate_parses_raw_when_available(self, mock_run):
        raw = TestParseRaw.raw_bytes(
            ["time", "v(input)", "v(collector)"],
            [[0.0, 0.0, 11.7]],
        )
        mock_run.return_value = spice_engine.SpiceResult(
            analysis="tran",
            success=True,
            engine="ngspice",
            log="No. of Data Rows : 1\n",
            raw=raw,
        )
        params = dict(spice_engine.DEFAULTS)
        result = spice_engine.simulate(params, "tran")
        self.assertTrue(result.success)
        self.assertIsNone(result.error)
        self.assertEqual(len(result.data["points"]), 1)
        self.assertAlmostEqual(result.data["points"][0]["vout_v"], 11.7)

    @patch("spice_engine.run_ngspice")
    def test_parse_failure_clears_success(self, mock_run):
        mock_run.return_value = spice_engine.SpiceResult(
            analysis="op",
            success=True,
            engine="ngspice",
            log="No. of Data Rows : 1\n",
        )

        def broken_parser(text, raw=None):
            raise ValueError("bad raw")

        with patch.dict(spice_engine._PARSERS, {"op": broken_parser}):
            result = spice_engine.simulate(dict(spice_engine.DEFAULTS), "op")
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertIn("parse error", result.error)


if __name__ == "__main__":
    unittest.main()
