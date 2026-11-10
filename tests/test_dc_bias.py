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
        self.assertAlmostEqual(r.vth, 2.1639344262295084, places=9)
        self.assertAlmostEqual(r.rth, 18.0327868852459, places=9)
        self.assertAlmostEqual(r.ib, 1.2298581462608458e-05, delta=1e-12)
        self.assertAlmostEqual(r.ic, 0.0012298581462608458, delta=1e-12)
        self.assertAlmostEqual(r.ie, 0.0012421567277234543, delta=1e-12)
        self.assertAlmostEqual(r.ve, 1.2421567277234544, places=6)
        self.assertAlmostEqual(r.vb, 1.9421567277234544, places=6)
        self.assertAlmostEqual(r.vc, 9.294312078226138, places=6)
        self.assertAlmostEqual(r.vce, 8.052155350502684, places=6)
        self.assertEqual(r.region, "ACTIVE")

    def test_cutoff_reports_zero_currents_and_divider_base(self):
        r = self.sample(r2_k=5.0)
        self.assertEqual(r.region, "CUTOFF")
        self.assertEqual(r.ib, 0.0)
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.ie, 0.0)
        self.assertEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vb, 12.0 * 5.0 / 105.0, places=9)
        self.assertEqual(r.vc, 12.0)
        self.assertEqual(r.vce, 12.0)
        self.assertAlmostEqual(r.vth, 12.0 * 5.0 / 105.0, places=9)
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

    def test_very_high_beta_approaches_the_emitter_stabilised_limit(self):
        r = self.sample(beta=10000.0)
        self.assertEqual(r.region, "ACTIVE")
        self.assertAlmostEqual(r.ic, 1.461153e-3, delta=1e-9)
        self.assertFalse(r.warnings)

    def test_rejects_non_physical_parameters(self):
        for bad in (
            dict(vcc=0.0), dict(vcc=-1.0), dict(r1_k=0.0), dict(r2_k=0.0),
            dict(rc_k=0.0), dict(re_k=0.0), dict(beta=0.0), dict(beta=-5.0),
            dict(vbe=0.0), dict(vbe=12.0), dict(vbe=20.0),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.sample(**bad)


if __name__ == "__main__":
    unittest.main()
