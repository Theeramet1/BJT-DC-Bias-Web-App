# Validation — BJT DC Bias Web App (Lab 03 + Lab 04)

เอกสารนี้บันทึกการตรวจสอบผลลัพธ์จริง ไม่ใช่การอธิบายว่าควรได้อะไร

---

## 1. ค่าอ้างอิงที่คำนวณด้วยมือ

เงื่อนไขร่วมทุกกรณี: **VCC = 12 V, RC = 2.2 kΩ, β = 100, VBE = 0.70 V**

---

### A1 · Voltage Divider Bias (โหมดเดิมจาก Lab 2)

อินพุต: R1 = 100 kΩ, R2 = 22 kΩ, RE = 1 kΩ

**ขั้นที่ 1 — แรงดันและความต้านทานสมมูลของตัวแบ่ง (Thevenin)**

```
VTH = 12 × 22 / (100 + 22) = 264 / 122 = 2.1639 V
RTH = 100 × 22 / (100 + 22) = 2200 / 122 = 18.0328 kΩ
```

**ขั้นที่ 2 — กระแสเบส (คำนึงการโหลดฐาน)**

```
IB = (VTH − VBE) / [RTH + (β + 1) × RE]
   = (2.1639 − 0.70) / [18 032.8 + 101 × 1 000]
   = 1.4639 / 119 032.8
   = 12.2986 µA
```

**ขั้นที่ 3 — กระแสและแรงดัน**

```
IC  = β × IB      = 100 × 12.2986 µA = 1.2299 mA
IE  = (β + 1) × IB = 101 × 12.2986 µA = 1.2422 mA
VE  = IE × RE     = 1.2422 mA × 1 kΩ = 1.2422 V
VB  = VE + VBE    = 1.2422 + 0.70    = 1.9422 V
VC  = VCC − IC×RC = 12 − 1.2299 mA × 2.2 kΩ = 9.2943 V
VCE = VC − VE     = 9.2943 − 1.2422  = 8.0521 V
```

**สรุปค่าอ้างอิง A1**

| ปริมาณ | ค่าที่คำนวณมือ | ค่าที่เว็บแสดง |
|---|---|---|
| VTH | 2.1639 V | 2.164 V |
| RTH | 18.0328 kΩ | 18.033 kΩ |
| VB | 1.9422 V | 1.942 V |
| VE | 1.2422 V | 1.242 V |
| VC | 9.2943 V | 9.294 V |
| VCE | 8.0521 V | 8.052 V |
| IC | 1.2299 mA | 1.230 mA |
| IE | 1.2422 mA | 1.242 mA |
| IB | 12.2986 µA | 12.300 µA |
| Region | ACTIVE | ACTIVE |

---

### A2 · Fixed Bias

อินพุต: RB = 1 MΩ

```
IB = (VCC − VBE) / RB = (12 − 0.70) / 1 000 000 = 11.3 µA
IC  = β × IB = 100 × 11.3 µA = 1.13 mA
IE  = (β + 1) × IB = 1.1413 mA
VE  = 0 V
VB  = VBE = 0.70 V
VC  = VCC − IC × RC = 12 − 1.13 mA × 2.2 kΩ = 9.514 V
VCE = VC − VE = 9.514 V
```

**สรุปค่าอ้างอิง A2**

| ปริมาณ | ค่าที่คำนวณมือ | ค่าที่เว็บแสดง |
|---|---|---|
| VB | 0.70 V | 0.700 V |
| VE | 0 V | 0.000 V |
| VC | 9.514 V | 9.514 V |
| VCE | 9.514 V | 9.514 V |
| IC | 1.13 mA | 1.130 mA |
| IE | 1.1413 mA | 1.141 mA |
| IB | 11.3 µA | 11.300 µA |
| Region | ACTIVE | ACTIVE |

---

### A3 · Emitter Bias

อินพุต: RB = 1 MΩ, RE = 1 kΩ

```
IB = (VCC − VBE) / [RB + (β + 1) × RE]
   = 11.3 / [1 000 000 + 101 × 1 000]
   = 11.3 / 1 101 000
   = 10.263 µA
IC  = 100 × 10.263 µA = 1.0263 mA
IE  = 101 × 10.263 µA = 1.0366 mA
VE  = 1.0366 mA × 1 kΩ = 1.0366 V
VB  = 1.0366 + 0.70 = 1.7366 V
VC  = 12 − 1.0263 mA × 2.2 kΩ = 9.7421 V
VCE = 9.7421 − 1.0366 = 8.7055 V
```

**สรุปค่าอ้างอิง A3**

| ปริมาณ | ค่าที่คำนวณมือ | ค่าที่เว็บแสดง |
|---|---|---|
| VB | 1.7366 V | 1.737 V |
| VE | 1.0366 V | 1.037 V |
| VC | 9.7421 V | 9.742 V |
| VCE | 8.7055 V | 8.705 V |
| IC | 1.0263 mA | 1.026 mA |
| IE | 1.0366 mA | 1.037 mA |
| IB | 10.263 µA | 10.263 µA |
| Region | ACTIVE | ACTIVE |

---

### A4 · Emitter Bias เปลี่ยน RE เป็น 2 kΩ

อินพุต: RB = 1 MΩ, RE = 2 kΩ (ค่าอื่นเท่า A3)

```
IB = 11.3 / [1 000 000 + 101 × 2 000]
   = 11.3 / 1 202 000
   = 9.401 µA   (ลดลงจาก A3)
IC  = 100 × 9.401 µA = 0.9401 mA  (ลดลง)
IE  = 101 × 9.401 µA = 0.9495 mA
VE  = 0.9495 mA × 2 kΩ = 1.899 V  (เพิ่มขึ้น)
VB  = 1.899 + 0.70 = 2.599 V
VC  = 12 − 0.9401 mA × 2.2 kΩ = 9.9318 V
VCE = 9.9318 − 1.899 = 8.0328 V
```

**ทิศทางที่คาดหมาย:** เปลี่ยน RE จาก 1 → 2 kΩ ทำให้ IC ลดลง (จาก 1.026 mA เป็น 0.940 mA) เพราะ RE ที่มากขึ้นเพิ่มตัวต้านทานในลูปฐาน-อีมิเตอร์ ทำให้ IB ลดลง

---

### A5 · ข้อมูลผิด (Fixed Bias, RB = 0)

อินพุต: RB = 0

ผลที่คาดหมาย: HTTP 200 + ข้อความ "ต้องมากกว่า 0" ใต้ช่อง RB เว็บไม่ล่ม ไม่มี Traceback

---

## 2. การตรวจผ่านเบราว์เซอร์ (Browser)

ทุกกรณีทดสอบผ่าน HTTP จริงด้วย Flask test client — ทุกกรณีตอบ **HTTP 200**

| กรณี | โหมด | อินพุต | ผลที่ได้ |
|------|------|--------|----------|
| GET / | — | — | HTTP 200 เห็นฟอร์มพร้อมตัวเลือกโหมด 3 แบบ |
| A1 | Divider | R1=100k, R2=22k, RE=1k | HTTP 200 แสดง VB 1.942 V, VC 9.294 V, VCE 8.052 V, ACTIVE |
| A2 | Fixed | RB=1M | HTTP 200 แสดง VB 0.700 V, VC 9.514 V, VCE 9.514 V, ACTIVE |
| A3 | Emitter | RB=1M, RE=1k | HTTP 200 แสดง VB 1.737 V, VC 9.742 V, VCE 8.705 V, ACTIVE |
| A5 | Fixed | RB=0 | HTTP 200 + ข้อความ "ต้องมากกว่า 0" ใต้ช่อง RB ไม่มี Traceback |

---

## 3. บันทึกการรันเทสต์จริง

คำสั่ง: `python -m unittest discover -s tests -v`

```
Ran 66 tests in 0.08s

OK
```

**การกระจายตัวของเทสต์**

- ฝั่งคณิต (`test_dc_bias.py`): **12 เทสต์** — แบ่งเป็น BiasNetwork (2), Fixed Bias (3), Emitter Bias (3), Divider Bias (4)
- ฝั่ง ngspice (`test_spice_engine.py`): **25 เทสต์** — netlist, subprocess, raw parser, version, simulate
- ฝั่ง HTTP (`test_web.py`): **29 เทสต์** — Index (10), Calculate (10), Validation (9)

---

## 4. การตรวจด้วยมือ (Browser Acceptance)

ต้องรัน Flask บนเครื่องก่อน:

```bash
python -m flask --app app run --debug
```

แล้วเปิด **http://127.0.0.1:5000/** ในเบราว์เซอร์

| การทดสอบ | ผล |
|---|---|
| `GET /` | HTTP 200 เห็นฟอร์มพร้อม dropdown เลือกโหมด 3 แบบ |
| เลือก Divider + ค่าตัวอย่าง | แสดง VB 1.942 V, VC 9.294 V, VCE 8.052 V, ACTIVE |
| เลือก Fixed + RB=1M | แสดง VB 0.700 V, VC 9.514 V, ACTIVE |
| เลือก Emitter + RB=1M, RE=1k | แสดง VB 1.737 V, VC 9.742 V, VCE 8.705 V, ACTIVE |
| `RB = 0` ในโหมด Fixed | HTTP 200 มีข้อความ "ต้องมากกว่า 0" ใต้ช่อง RB |
| โหมดไม่รู้จัก | HTTP 200 มีข้อความแจ้งโหมดไม่ถูกต้อง |

---

## 5. Lab 04 — ตรวจสอบการจำลองจริงด้วย ngspice (B1–B8)

ค่าตัวอย่างที่ใช้ทุกกรณี: **VCC = 12 V, R1 = 100 kΩ, R2 = 22 kΩ, RC = 2.2 kΩ,
RE = 1 kΩ, RL = 10 kΩ, Cin = Cout = 10 µF, amp = 10 mV, f = 1 kHz,
β = 100, VBE = 0.70 V** หน่วยที่ข้ามเข้า `spice_engine` เป็นโวลต์/โอห์ม/ฟาราด
(10 µF → `1e-05` ใน netlist, 10 mV → `0.01`)

### B1 — เลือกวิธีวิเคราะห์ได้จากหน้าเว็บ

`GET /` → HTTP 200 มี `<select name="analysis">` ทั้งสี่ค่า: `analytical`,
`spice_op`, `spice_ac`, `spice_tran` เมื่อเลือก `spice_*` จะเห็นช่องเพิ่ม
`RL`, `Cin`, `Cout`, amplitude และ frequency (ทดสอบจริงด้วย Flask test client)

### B2 — ผลเชิงวิเคราะห์ของ Lab 03 ยังไม่เปลี่ยนแปลง

Divider + `analytical` → VB 1.942 V, VC 9.294 V, VCE 8.052 V, `ACTIVE`
(Fixed 0.700/9.514, Emitter 1.737/9.742) แสดงในบล็อกที่มีป้าย **analytical**
แยกจากบล็อก **ngspice** เสมอ

### B3 — เรียก solver แบบ batch จริง

`run_ngspice()` เรียก `ngspice -b -o run.log -r run.raw circuit.cir` แบบ
`subprocess.run([...])` (ไม่มี `shell=True`), `cwd` เป็น temp dir แยกต่อครั้ง,
`timeout=60` วินาที ตรวจจาก log จริงว่ามี `No. of Data Rows` และไฟล์
`run.raw` ถูกสร้างขึ้น เนื่องจาก ngspice ข้าม `.print` เมื่อมี `-r`
('.print line ignored since rawfile was produced.') โปรแกรมจึงอ่านค่าจาก
raw binary แทน — ไม่มีการเดาหรือสร้างข้อมูลขึ้นเอง

### B4 — `.op` ผลจาก ngspice จริง

```
VB = 1.949112 V   VE = 1.289454 V   VC = 9.189410 V
VCE = 7.899956 V  I(V1) = -1.378 mA
```

raw file มี 1 point / 8 variables (`v(vcc)`, `v(base)`, `v(collector)`,
`v(emitter)`, `v(output)`, `v(input)`, `i(vin)`, `i(v1)`) ค่าต่างจากแบบ
วิเคราะห์เล็กน้อย (VB 1.949 vs 1.942) ซึ่งเป็นที่คาดหมายเพราะแบบจำลอง
ทรานซิสเตอร์ใน SPICE ไม่ใช่ β/VBE คงที่

### B5 — `.ac` ผลจาก ngspice จริง

301 จุด ความถี 1–1000 Hz (`dec 50`) ที่ 1 Hz ได้ gain 1.3926 V/V,
phase −139.42° เกิดจาก `|v(collector)| / |v(input)|` และเฟสของสัญญาณ
จริงจาก raw file กราฟ Plotly วาดจาก `spice.data['points']` โดยตรง
(ตรวจในเบราว์เซอร์: `.js-plotly-plot` 1 อัน, `.trace` 1 เส้น, 301 จุด)
Plotly ถูกเก็บไว้ใน `static/plotly.min.js` และโหลดใน `<head>` ก่อน inline script
จึงไม่พึ่งพา CDN (CDN ถูกบล็อกในเบราว์เซอร์ทดสอบ → เคยทำให้กราฟว่าง)

### B6 — `.tran` ผลจาก ngspice จริง

1008 จุด ช่วงเวลา 0–0.01 s (10 คาบของ 1 kHz) step 10 µs
(100 ตัวอย่างต่อคาบ — ไม่เกิด aliasing แบบ `.tran 0.001 1` เดิม)
จุดแรก `vin = 0 V, vout = 11.769 V`; จุดสุดท้าย `vin ≈ 0, vout ≈ 11.77 V`
(ขึ้นกับจุดหยุดของ solver เล็กน้อย)
กราฟแสดงทั้ง V(IN) และ V(OUT) จากคอลัมน์ `v(input)` / `v(collector)`
(ตรวจในเบราว์เซอร์: `.js-plotly-plot` 1 อัน, `.trace` 2 เส้น, 1008 จุด)

### B7 — ความผิดพลาดต้องไม่ทิ้งกราฟเก่า

- ไม่มี ngspice → `SpiceResult(success=False)` พร้อมข้อความ error
- หมดเวลา / log ว่าง / parse พัง → `success=False`, `data=None`
  (test `test_parse_failure_clears_success`)
- `POST /calculate` ในสถานะ error → HTTP 200, แสดง **Error**,
  ไม่มี `id="ac-plot"`/`id="tran-plot"` และไม่มีผล analytical ปนมา
- ช่อง SPICE ที่ขาด/เป็นศูนย์ → field error HTTP 200 ค่าที่พิมพ์ยังอยู่

### B8 — สรุปผลรันจริง

```
python -m unittest discover -s tests -v
Ran 66 tests ... OK
```

ตรวจผ่านเบราว์เซอร์: `GET /`, เปลี่ยน `<select name="analysis">` → ไป `/?mode=divider&analysis=...`,
submit `.op`/`.ac`/`.tran` กับ ngspice จริง ได้ HTTP 200 ทุกครั้ง
แสดง `Engine: ngspice version ngspice-47` (อ่านจาก header ของ `run.raw`
เพราะ `ngspice --version` ไม่พิมพ์อะไรบน MSYS2 build) มีกราฟจากข้อมูลจำลองจริง
(AC 1 trace / 301 จุด, TRAN 2 traces / 1008 จุด) ไม่มี console error หรือ Traceback

