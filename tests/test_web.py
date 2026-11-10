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
        self.assertIn('type="submit"', body)

    def test_form_is_prefilled_with_the_sample_values(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn('value="100"', body)
        self.assertIn('value="0.70"', body)


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


if __name__ == "__main__":
    unittest.main()
