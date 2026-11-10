# Validation — BJT DC Bias Web App

เอกสารนี้บันทึกการตรวจสอบผลลัพธ์จริง ไม่ใช่การอธิบายว่าควรได้อะไร

---

## 1. ค่าอ้างอิงที่คำนวณด้วยมือ (A3)

ข้อมูลทดลองจากใบงาน: **VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ,
RC = 2.2 kΩ, RE = 1 kΩ, β = 100, VBE = 0.70 V**

**ขั้นที่ 1 — แรงดันจากตัวแบ่ง (ละเวงการโหลดกระแสเบส)**

```
VTH = 12 × 22 / (100 + 22) = 264 / 122 = 2.1639 V
RTH = 100 × 22 / (100 + 22) = 2200 / 122 = 18.0328 kΩ
VB  = VTH = 2.1639 V
```

**ขั้นที่ 2 — แรงดันและกระแสที่อีมิเตอร์**

```
VE  = VB − VBE = 2.1639 − 0.70 = 1.4639 V
IE  = VE ÷ RE  = 1.4639 V ÷ 1 kΩ = 1.4639 mA
```

**ขั้นที่ 3 — กระแสคอลเลกเตอร์และเบส**

```
IC  = β ÷ (β + 1) × IE = 100 ÷ 101 × 1.4639 mA = 1.4494 mA
IB  = IC ÷ β = 1.4494 mA ÷ 100 = 14.494 µA
```

**ขั้นที่ 4 — แรงดันที่คอลเลกเตอร์และ VCE**

```
VC  = VCC − IC × RC = 12 − 1.4494 mA × 2.2 kΩ = 12 − 3.1887 = 8.8113 V
VCE = VC − VE = 8.8113 − 1.4639 = 7.3474 V
```

**สรุปค่าอ้างอิง**

| ปริมาณ | ค่าที่คำนวณมือ | ค่าที่เว็บแสดง |
|---|---|---|
| VTH | 2.1639 V | 2.164 V |
| RTH | 18.0328 kΩ | 18.033 kΩ |
| VB | 2.1639 V | 2.164 V |
| VE | 1.4639 V | 1.464 V |
| VC | 8.8113 V | 8.811 V |
| VCE | 7.3474 V | 7.347 V |
| IC | 1.4494 mA | 1.449 mA |
| IE | 1.4639 mA | 1.464 mA |
| IB | 14.494 µA | 14.494 µA |
| Region | ACTIVE (VCE ≫ 0.7 V) | ACTIVE |

ค่าตรงกันทุกหลักที่แสดง (ปัดเศษทศนิยม 3 ตำแหน่ง)

---

## 2. กรณีข้อมูลผิด (A4)

ทดสอบผ่าน HTTP จริงด้วย `POST /calculate` — ทุกกรณีตอบ **HTTP 200**
หน้าเว็บไม่ล้ม และค่าที่พิมพ์ไว้ยังอยู่ในฟอร์ม

| อินพุตที่ส่ง | ผลที่ได้ |
|---|---|
| `r1 = 0` | HTTP 200 + ข้อความ "ต้องมากกว่า 0" ใต้ช่อง R1 |
| `vcc = abc` | HTTP 200 + ข้อความ "ต้องเป็นตัวเลข" |
| `rc = 2,2` (ลูกน้ำ) | HTTP 200 + ข้อความ "ต้องเป็นตัวเลข" |
| `r1 = 1e400` | HTTP 200 + ข้อความ "ต้องเป็นตัวเลข" (ค่าอนันต์ถูกปฏิเสธ) |
| `vcc = " 12 "` (มีช่องว่าง) | ยอมรับ — คำนวณได้ 2.164 V ตามปกติ |
| ส่งฟอร์มว่าง | HTTP 200 + ข้อความ "กรุณากรอกค่านี้" ครบทั้ง 7 ช่อง |
| `rc = oops, r2 = 33` | HTTP 200 + error ที่ RC และช่อง R2 ยังแสดง `33` |

---

## 3. กรณีนอกช่วง Forward-Active (A5)

| กรณี | อินพุต | ผล |
|---|---|---|
| **Cutoff** | R2 = 5 kΩ → VTH = 12×5/105 = **0.5714 V** ≤ VBE 0.70 V | Region `CUTOFF`, IB=IC=IE=0, VE=0, VB=VTH=0.571 V, VC=VCE=12 V + คำเตือนว่าแบบจำลองใช้ไม่ได้ |
| **Saturation** | RC = 15 kΩ → VC = 12 − 1.4494m×15k = −9.741 V, VCE = **−11.205 V** < 0.3 V | Region `SATURATION` + แบนเนอร์เตือนว่า VCE ต่ำกว่า 0.3 V และค่าไม่น่าเชื่อถือ |
| **ใกล้จุดอิ่มตัว** | RC = 6.92 kΩ → VCE = **0.506 V** (ระหว่าง 0.3–0.7 V) | Region `ACTIVE` + คำเตือนว่าอยู่ใกล้ช่วงอิ่มตัว |

หมายเหตุ: ในกรณี Saturation โปรแกรม **ไม่แก้สมการซ้ำ** ตามที่ใบงานกำหนด
แต่รายงานตัวเลขตามสมการพร้อมเตือนว่าสมมติฐาน Forward-Active ถูกทำลาย

---

## 4. บันทึกการรันเทสต์จริง (A6)

คำสั่ง: `python -m unittest discover -s tests -v`

```
test_divider_network_for_sample_values (test_dc_bias.BiasNetworkTests...) ... ok
test_equal_resistors_halve_the_supply (test_dc_bias.BiasNetworkTests...) ... ok
test_cutoff_reports_zero_currents_and_divider_base (test_dc_bias.OperatingPointTests...) ... ok
test_large_collector_resistor_is_reported_as_saturation (test_dc_bias.OperatingPointTests...) ... ok
test_point_just_above_saturation_stays_active_with_caution (test_dc_bias.OperatingPointTests...) ... ok
test_rejects_non_physical_parameters (test_dc_bias.OperatingPointTests...) ... ok
test_sample_values_match_simplified_divider_method (test_dc_bias.OperatingPointTests...) ... ok
test_very_high_beta_approaches_ie_limit (test_dc_bias.OperatingPointTests...) ... ok
test_numbers_come_from_python_not_the_template (test_web.CalculateTests...) ... ok
test_sample_input_renders_the_computed_operating_point (test_web.CalculateTests...) ... ok
test_form_is_prefilled_with_the_sample_values (test_web.IndexTests...) ... ok
test_get_root_serves_the_form (test_web.IndexTests...) ... ok
test_comma_decimal_is_rejected_with_a_readable_error (test_web.ValidationTests...) ... ok
test_empty_form_reports_every_field (test_web.ValidationTests...) ... ok
test_entered_values_survive_a_failed_submit (test_web.ValidationTests...) ... ok
test_infinite_number_is_rejected (test_web.ValidationTests...) ... ok
test_non_numeric_supply_voltage_is_reported (test_web.ValidationTests...) ... ok
test_whitespace_around_a_number_is_accepted (test_web.ValidationTests...) ... ok
test_zero_resistor_is_reported_without_crashing (test_web.ValidationTests...) ... ok

----------------------------------------------------------------------
Ran 19 tests in 0.042s

OK
```

**การกระจายตัวของเทสต์**

- ฝั่งคณิต (`test_dc_bias.py`): **8 เทสต์** — เกินเกณฑ์ขั้นต่ำ 3
- ฝั่ง HTTP (`test_web.py`): **11 เทสต์** — เกินเกณฑ์ขั้นต่ำ 1

**เทสต์ที่กันการโกงเป็นพิเศษ**

- `test_numbers_come_from_python_not_the_template` — เปลี่ยนอินพุตเป็น
  VCC=15, R1=47 แล้วยืนยันว่า `2.164` **หายไป** จากหน้า ถ้ามีใครฝังตัวเลข
  ไว้ใน template เทสต์นี้จะจับได้ทันที
- `test_sample_values_match_simplified_divider_method` — assert กระแสเป็น **แอมแปร์**
  (`1.4494e-3`) ไม่ใช่ mA ถ้าโค้ดคืนหน่วยผิดจะต่างกัน 1000 เท่าและ fail

---

## 5. การตรวจด้วยตา (Browser)

| การทดสอบ | ผล |
|---|---|
| `GET /` | HTTP 200 เห็นฟอร์ม 7 ช่อง พร้อมค่าตัวอย่าง |
| `POST /calculate` ค่าตัวอย่าง | HTTP 200 แสดง VB 2.164 V, VC 8.811 V, VCE 7.347 V, ACTIVE |
| `r1 = 0` | HTTP 200 หน้าไม่ล้ม มี error ใต้ช่อง R1 |
| `rc = 2,2` | HTTP 200 มี error "ต้องเป็นตัวเลข" |
| ส่งฟอร์มว่าง | HTTP 200 มี error ครบ 7 ช่อง |
| `rc = 15` | HTTP 200 แสดง SATURATION + แบนเนอร์เตือน |
