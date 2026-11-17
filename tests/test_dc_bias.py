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


class FixedBiasTests(unittest.TestCase):
    def params(self, **overrides):
        p = dict(vcc=12.0, rb_k=1000.0, rc_k=2.2, beta=100.0, vbe=0.70)
        p.update(overrides)
        return p

    def test_fixed_bias_sample_values(self):
        r = dc_bias.fixed_bias(**self.params())
        # IB = (12 - 0.7) / 1,000,000 = 11.3 µA
        self.assertAlmostEqual(r.ib, 1.13e-5, delta=1e-15)
        self.assertAlmostEqual(r.ic, 0.00113, delta=1e-15)
        self.assertAlmostEqual(r.ie, 0.0011413, delta=1e-15)
        self.assertAlmostEqual(r.ve, 0.0, places=9)
        self.assertAlmostEqual(r.vb, 0.70, places=9)
        self.assertAlmostEqual(r.vc, 12.0 - 0.00113 * 2200, places=6)
        self.assertAlmostEqual(r.vce, r.vc, places=6)
        self.assertEqual(r.region, "ACTIVE")
        self.assertFalse(r.warnings)

    def test_fixed_bias_zero_rb_rejected(self):
        with self.assertRaises(ValueError):
            dc_bias.fixed_bias(**self.params(rb_k=0.0))

    def test_fixed_bias_high_rb_gives_low_ic(self):
        r = dc_bias.fixed_bias(**self.params(rb_k=10000.0))
        self.assertAlmostEqual(r.ib, 1.13e-6, delta=1e-12)
        self.assertAlmostEqual(r.ic, 1.13e-4, delta=1e-12)


class EmitterBiasTests(unittest.TestCase):
    def params(self, **overrides):
        p = dict(vcc=12.0, rb_k=1000.0, re_k=1.0, rc_k=2.2,
                 beta=100.0, vbe=0.70)
        p.update(overrides)
        return p

    def test_emitter_bias_sample_values(self):
        r = dc_bias.emitter_bias(**self.params())
        # IB = 11.3 / (1,000,000 + 101*1000) = 11.3 / 1,101,000
        self.assertAlmostEqual(r.ib, 1.0263396911898274e-05, delta=1e-12)
        self.assertAlmostEqual(r.ic, 0.0010263396911898274, delta=1e-12)
        self.assertAlmostEqual(r.ie, 0.0010366030881017257, delta=1e-12)
        self.assertAlmostEqual(r.ve, 1.0366030881017257, places=6)
        self.assertAlmostEqual(r.vb, 1.7366030881017257, places=6)
        self.assertAlmostEqual(r.vc, 9.74205227958238, places=6)
        self.assertAlmostEqual(r.vce, 8.705449191480654, places=6)
        self.assertEqual(r.region, "ACTIVE")
        self.assertFalse(r.warnings)

    def test_emitter_bias_re_increase_reduces_ic(self):
        r1 = dc_bias.emitter_bias(**self.params(re_k=1.0))
        r2 = dc_bias.emitter_bias(**self.params(re_k=2.0))
        # A4: เปลี่ยน RE จาก 1 เป็น 2 kΩ แล้ว IC ควรลดลง
        self.assertLess(r2.ic, r1.ic)
        self.assertGreater(r2.ve, r1.ve)

    def test_emitter_bias_zero_values_rejected(self):
        with self.assertRaises(ValueError):
            dc_bias.emitter_bias(**self.params(rb_k=0.0))
        with self.assertRaises(ValueError):
            dc_bias.emitter_bias(**self.params(re_k=0.0))


class DividerBiasTests(unittest.TestCase):
    def params(self, **overrides):
        p = dict(vcc=12.0, r1_k=100.0, r2_k=22.0, rc_k=2.2, re_k=1.0,
                 beta=100.0, vbe=0.70)
        p.update(overrides)
        return p

    def test_divider_loading_aware_sample_values(self):
        r = dc_bias.divider_bias(**self.params())
        # Loading-aware: IB = (VTH - VBE) / [RTH + (β+1)RE]
        # VTH = 2.1639 V, RTH = 18.033 kΩ
        # IB = 1.4639 / (18033 + 101000) = 12.299 µA
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
        self.assertFalse(r.warnings)

    def test_cutoff_reports_zero_currents_and_divider_base(self):
        r = dc_bias.divider_bias(**self.params(r2_k=5.0))
        self.assertEqual(r.region, "CUTOFF")
        self.assertEqual(r.ib, 0.0)
        self.assertEqual(r.ic, 0.0)
        self.assertEqual(r.ie, 0.0)
        self.assertEqual(r.ve, 0.0)
        self.assertAlmostEqual(r.vb, 12.0 * 5.0 / 105.0, places=9)
        self.assertEqual(r.vc, 12.0)
        self.assertEqual(r.vce, 12.0)
        self.assertTrue(r.warnings)

    def test_large_collector_resistor_is_reported_as_saturation(self):
        r = dc_bias.divider_bias(**self.params(rc_k=15.0))
        self.assertEqual(r.region, "SATURATION")
        self.assertTrue(r.warnings)
        self.assertLess(r.vce, dc_bias.VCE_SATURATION)

    def test_rejects_non_physical_parameters(self):
        for bad in (
            dict(vcc=0.0), dict(vcc=-1.0), dict(r1_k=0.0), dict(r2_k=0.0),
            dict(rc_k=0.0), dict(re_k=0.0), dict(beta=0.0), dict(beta=-5.0),
            dict(vbe=0.0), dict(vbe=12.0), dict(vbe=20.0),
        ):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                dc_bias.divider_bias(**self.params(**bad))


if __name__ == "__main__":
    unittest.main()
