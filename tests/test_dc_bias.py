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

    def test_sample_values_match_simplified_divider_method(self):
        r = self.sample()
        # Simplified: VB = VTH (ignore base current loading)
        self.assertAlmostEqual(r.vth, 2.1639344262295084, places=9)
        self.assertAlmostEqual(r.rth, 18.0327868852459, places=9)
        self.assertAlmostEqual(r.vb, 2.1639344262295084, places=9)
        self.assertAlmostEqual(r.ve, 1.4639344262295084, places=9)
        self.assertAlmostEqual(r.ie, 0.0014639344262295084, delta=1e-12)
        self.assertAlmostEqual(r.ic, 0.0014494400269599094, delta=1e-12)
        self.assertAlmostEqual(r.ib, 0.000014494400269599094, delta=1e-12)
        self.assertAlmostEqual(r.vc, 8.8112319406882, places=6)
        self.assertAlmostEqual(r.vce, 7.347297514458692, places=6)
        self.assertEqual(r.region, "ACTIVE")
        self.assertFalse(r.warnings)

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
        # With simplified method, IC is higher so VCE drops faster.
        # rc_k=6.92 gives VCE ≈ 0.506 V (between 0.3 and 0.7 V).
        r = self.sample(rc_k=6.92)
        self.assertEqual(r.region, "ACTIVE")
        self.assertTrue(r.warnings)
        self.assertGreater(r.vce, dc_bias.VCE_SATURATION)
        self.assertLess(r.vce, dc_bias.VCE_NEAR_SATURATION)

    def test_very_high_beta_approaches_ie_limit(self):
        r = self.sample(beta=10000.0)
        self.assertEqual(r.region, "ACTIVE")
        # IC asymptotes to VE/RE = (VTH-VBE)/RE ≈ 1.464 mA
        self.assertAlmostEqual(r.ic, 1.463788e-3, delta=1e-9)
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
