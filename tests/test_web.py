import unittest

import app as webapp


class IndexTests(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()

    def test_get_root_serves_the_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        for name in ("vcc", "rc", "beta", "vbe"):
            self.assertIn(f'name="{name}"', body)
        self.assertIn('name="mode"', body)
        self.assertIn('<form', body)
        self.assertIn('type="submit"', body)

    def test_form_has_mode_selector(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('value="divider"', body)
        self.assertIn('value="fixed"', body)
        self.assertIn('value="emitter"', body)

    def test_divider_mode_shows_r1_r2_re(self):
        body = self.client.get("/?mode=divider").get_data(as_text=True)
        self.assertIn('name="r1"', body)
        self.assertIn('name="r2"', body)
        self.assertIn('name="re"', body)

    def test_fixed_mode_shows_rb_not_r1_r2(self):
        body = self.client.get("/?mode=fixed").get_data(as_text=True)
        self.assertIn('name="rb"', body)
        self.assertNotIn('name="r1"', body)
        self.assertNotIn('name="r2"', body)

    def test_emitter_mode_shows_rb_and_re(self):
        body = self.client.get("/?mode=emitter").get_data(as_text=True)
        self.assertIn('name="rb"', body)
        self.assertIn('name="re"', body)
        self.assertNotIn('name="r1"', body)
        self.assertNotIn('name="r2"', body)

    def test_form_is_prefilled_with_the_sample_values(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('value="100"', body)
        self.assertIn('value="0.70"', body)


class CalculateTests(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.valid_divider = {
            "mode": "divider",
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
            "re": "1", "beta": "100", "vbe": "0.70",
        }
        self.valid_fixed = {
            "mode": "fixed",
            "vcc": "12", "rb": "1000", "rc": "2.2",
            "beta": "100", "vbe": "0.70",
        }
        self.valid_emitter = {
            "mode": "emitter",
            "vcc": "12", "rb": "1000", "re": "1", "rc": "2.2",
            "beta": "100", "vbe": "0.70",
        }

    def test_divider_mode_renders_computed_operating_point(self):
        response = self.client.post("/calculate", data=self.valid_divider)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        # Loading-aware divider: VB ≈ 1.942 V, VC ≈ 9.294 V, VCE ≈ 8.052 V
        self.assertIn("1.942", body)
        self.assertIn("9.294", body)
        self.assertIn("8.052", body)
        self.assertIn("ACTIVE", body)
        self.assertIn("Voltage Divider", body)

    def test_fixed_mode_renders_computed_operating_point(self):
        response = self.client.post("/calculate", data=self.valid_fixed)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        # Fixed: IB = 11.3 µA, IC = 1.13 mA, VB = 0.70 V, VC ≈ 9.514 V
        self.assertIn("0.700", body)
        self.assertIn("9.514", body)
        self.assertIn("1.130", body)
        self.assertIn("ACTIVE", body)
        self.assertIn("Fixed Bias", body)

    def test_emitter_mode_renders_computed_operating_point(self):
        response = self.client.post("/calculate", data=self.valid_emitter)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        # Emitter: VB ≈ 1.737 V, VC ≈ 9.742 V, VCE ≈ 8.705 V
        self.assertIn("1.737", body)
        self.assertIn("9.742", body)
        self.assertIn("8.705", body)
        self.assertIn("ACTIVE", body)
        self.assertIn("Emitter Bias", body)

    def test_numbers_come_from_python_not_the_template(self):
        changed = dict(self.valid_divider, vcc="15", r1="47")
        body = self.client.post("/calculate", data=changed).get_data(as_text=True)
        self.assertNotIn("1.942", body)
        self.assertIn("VCE", body)

    def test_unknown_mode_rejected(self):
        bad = dict(self.valid_divider, mode="nonsense")
        response = self.client.post("/calculate", data=bad)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("โหมด", body)
        self.assertNotIn("Traceback", body)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.client = webapp.app.test_client()
        self.valid_divider = {
            "mode": "divider",
            "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2",
            "re": "1", "beta": "100", "vbe": "0.70",
        }
        self.valid_fixed = {
            "mode": "fixed",
            "vcc": "12", "rb": "1000", "rc": "2.2",
            "beta": "100", "vbe": "0.70",
        }
        self.valid_emitter = {
            "mode": "emitter",
            "vcc": "12", "rb": "1000", "re": "1", "rc": "2.2",
            "beta": "100", "vbe": "0.70",
        }

    def post(self, mode="divider", **overrides):
        base = {
            "divider": self.valid_divider,
            "fixed": self.valid_fixed,
            "emitter": self.valid_emitter,
        }[mode]
        data = dict(base)
        data.update({k: v for k, v in overrides.items()})
        return self.client.post("/calculate", data=data)

    def test_zero_resistor_rejected_in_divider(self):
        response = self.post("divider", r1="0")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("มากกว่า", body)
        self.assertNotIn("Traceback", body)

    def test_zero_rb_rejected_in_fixed(self):
        response = self.post("fixed", rb="0")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("มากกว่า", body)
        self.assertNotIn("Traceback", body)

    def test_non_numeric_rejected(self):
        body = self.post("divider", vcc="abc").get_data(as_text=True)
        self.assertIn("ตัวเลข", body)

    def test_whitespace_accepted(self):
        body = self.post("divider", vcc=" 12 ").get_data(as_text=True)
        self.assertIn("1.942", body)

    def test_comma_decimal_rejected(self):
        body = self.post("divider", rc="2,2").get_data(as_text=True)
        self.assertIn("ตัวเลข", body)

    def test_infinite_number_rejected(self):
        body = self.post("divider", r1="1e400").get_data(as_text=True)
        self.assertIn("ตัวเลข", body)

    def test_empty_form_reports_every_field(self):
        response = self.client.post("/calculate", data={"mode": "divider"})
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertEqual(body.count('class="field-error"'), 7)

    def test_entered_values_survive_failed_submit(self):
        body = self.post("fixed", rb="oops", rc="33").get_data(as_text=True)
        self.assertIn('value="33"', body)
        self.assertIn('value="oops"', body)

    def test_emitter_mode_only_requires_relevant_fields(self):
        # Emitter mode should not complain about missing r1/r2
        response = self.client.post("/calculate", data=self.valid_emitter)
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("1.737", body)


if __name__ == "__main__":
    unittest.main()
