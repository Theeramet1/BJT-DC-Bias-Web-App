# BJT DC Bias Web App (Lab 03 + Lab 04)

เว็บแอป Flask สำหรับทรานซิสเตอร์ BJT NPN แบบ Common Emitter สองส่วน:

- **Lab 03 — ผลเชิงวิเคราะห์**: คำนวณ DC Operating Point ของสามวงจรไบอัส
  (Voltage Divider, Fixed Bias, Emitter Bias) ด้วย Python ฝั่งเซิร์ฟเวอร์
- **Lab 04 — จำลองจริงด้วย ngspice**: วงจรอ้างอิง Voltage Divider แบบมี
  `RL`, `Cin`, `Cout` และแหล่งสัญญาณ รัน `.op`, `.ac`, `.tran` แบบ batch
  แล้วแสดงค่าที่อ่านจากไฟล์ `run.raw` จริง (ไม่มีค่าที่สร้างขึ้นเอง)

ผลทั้งสองแบบแสดงแยกบล็อกและมีป้ายกำกับชัดเจน (`analytical` / `ngspice`)

---

## วงจรที่รองรับ

| วิธีวิเคราะห์ | ตัวเลือก | ผลที่แสดง |
|---|---|---|
| `analytical` | Divider / Fixed / Emitter | VB, VE, VC, VCE, IC, IE, IB + region/warning |
| `spice_op` | Voltage Divider | node voltages จาก ngspice `.op`, VCE, I(V1) |
| `spice_ac` | Voltage Divider | กราฟ gain/phase vs frequency จาก `.ac` จริง |
| `spice_tran` | Voltage Divider | กราฟ V(IN)/V(OUT) vs time จาก `.tran` จริง |

 SPICE ใช้วงจรอ้างอิงเดียว: `V1 → RC → Q1(RE) → COUT → RL → กราวด์`,
 `R1/R2` แบ่งแรงดันที่เบส, `CIN` ต่อแหล่งสัญญาณเข้าเบส
 (แบบจำลองทรานซิสเตอร์ `IS=1e-14 BF=100 VAF=100`)

 ผลลัพธ์อ่านจาก `run.raw` ที่ ngspice เขียนจริง (เพราะ `-r` ทำให้ ngspice ข้าม
 `.print`) และแสดงเวอร์ชัน solver จาก header ของ raw file — ไม่มีการสร้างข้อมูล
 ขึ้นเอง กราฟใช้ Plotly ที่เก็บใน `static/plotly.min.js` จึงทำงานได้โดยไม่ต้อง
 เชื่อมต่อ CDN

---

## สมการที่ใช้ (Lab 03 — แบบจำลอง Forward-Active, β และ VBE คงที่)

### Fixed Bias
```
IB = (VCC − VBE) / RB
IC = β × IB
IE = (β + 1) × IB
VE = 0
VB = VBE
VC = VCC − IC × RC
VCE = VC − VE
```

### Emitter Bias
```
IB = (VCC − VBE) / [RB + (β + 1) × RE]
IC = β × IB
IE = (β + 1) × IB
VE = IE × RE
VB = VE + VBE
VC = VCC − IC × RC
VCE = VC − VE
```

### Voltage Divider Bias (คำนึงกระแสเบสโหลดตัวแบ่ง)
```
VTH = VCC × R2 / (R1 + R2)
RTH = R1 × R2 / (R1 + R2)
IB = (VTH − VBE) / [RTH + (β + 1) × RE]
IC = β × IB
IE = (β + 1) × IB
VE = IE × RE
VB = VE + VBE
VC = VCC − IC × RC
VCE = VC − VE
```

---

## สิ่งที่ต้องมี

- Python 3.10 ขึ้นไป (ทดสอบบน 3.14.2)
- Flask (ติดตั้งผ่าน `requirements.txt`)
- **ngspice** สำหรับโหมด `spice_*`:
  - Windows: `winget install MSYS2.MSYS2` แล้วใน MSYS2 UCRT64:
    `pacman -S mingw-w64-ucrt-x86_64-ngspice`
    (ตำแหนนที่ใช้คือ `C:\msys64\ucrt64\bin\ngspice.exe`)
  - Linux/macOS: `apt install ngspice` / `brew install ngspice`
  - ถ้าอยู่ตำแหน่งอื่น ตั้ง environment variable `NGSPICE_EXE` ให้ชี้ถึง executable

---

## ติดตั้งและรัน

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate

python -m pip install -r requirements.txt
python -m flask --app app run --debug
```

เปิดเบราว์เซอร์ที่ **http://127.0.0.1:5000/**

> ⚠️ **เซิร์ฟเวอร์ต้องรันบนเครื่องคุณเอง** ถึงจะเปิด `http://127.0.0.1:5000/` ในเบราว์เซอร์ได้
> คำสั่ง `python -m flask --app app run --debug` ต้องรันค้างไว้ใน Terminal ขณะใช้งาน
> Flask debug server ใช้สำหรับพัฒนาเท่านั้น ไม่ควรเปิดสู่เครือข่ายสาธารณะ

> ⚠️ **ห้ามเปิด `templates/index.html` ด้วยการ double-click**
> ไฟล์นั้นเป็นเพียง Jinja template ที่เซิร์ฟเวอร์นำไป render

ตัวอย่างการใช้งาน: เลือก `Voltage Divider Bias`, วิธีวิเคราะห์
`DC Operating Point (ngspice .op)` แล้วกด **Calculate DC Bias**
(ค่าตัวอย่างในฟอร์มใช้ได้เลย) — เปลี่ยนวิธีวิเคราะห์เป็น `.ac` หรือ `.tran`
เพื่อดูกราฟจากการจำลองจริง

---

## รันเทสต์

```bash
python -m unittest discover -s tests -v
```

ต้องได้ `Ran 66 tests ... OK`

(12 คณิต + 25 ngspice adapter + 29 HTTP; เทสต์ ngspice ใช้ mock จึงไม่ต้องมี
ngspice ติดตั้งเพื่อรันชุดเทสต์ — แต่ต้องมีเพื่อใช้โหมด `spice_*` ในเว็บ)

---

## หน่วยของข้อมูลนำเข้า

| ช่อง | ความหมาย | หน่วย |
|---|---|---|
| VCC | แรงดันเลี้ยงวงจร | V |
| R1, R2, RB, RC, RE, RL | ตัวต้านทาน | **kΩ** |
| Cin, Cout | ตัวเก็บประจุ | **µF** |
| Source amplitude | แอมพลิจูดแหล่งสัญญาณ (peak) | **mV** |
| Source frequency | ความถี่แหล่งสัญญาณ | **Hz** |
| β | อัตราขยายกระแส (hFE) | ไม่มีหน่วย |
| VBE | แรงดันตกคร่อมรอยต่อเบส–อีมิเตอร์ | V |

ค่าตัวอย่างจากใบงาน: VCC=12, RC=2.2, β=100, VBE=0.70, RL=10,
Cin=Cout=10, amplitude=10, frequency=1000

---

## กฎการแบ่งช่วงการทำงาน (ผลแบบวิเคราะห์)

| เงื่อนไข | Region | สิ่งที่เว็บแสดง |
|---|---|---|
| `VTH ≤ VBE` (Divider) | `CUTOFF` | IB=IC=IE=0, VB=VTH, VC=VCE=VCC + คำเตือน |
| `VCE < 0.3 V` | `SATURATION` | แสดงตัวเลข แต่เตือนว่าแบบจำลองใช้ไม่ได้ |
| `0.3 ≤ VCE < 0.7 V` | `ACTIVE` | แสดงตัวเลข + เตือนว่าใกล้จุดอิ่มตัว |
| `VCE ≥ 0.7 V` | `ACTIVE` | แสดงตัวเลขปกติ |

---

## โครงสร้างไฟล์

```
app.py            Flask routes, อ่านฟอร์ม, เลือก analytical/spice, error, render
dc_bias.py        สมการเชิงวิเคราะห์ล้วน (ไม่รู้จัก Flask/HTML/ngspice)
spice_engine.py   สร้าง netlist, เรียก ngspice แบบ batch, อ่าน run.raw
templates/        index.html — ฟอร์ม + ผลลัพธ์ + กราฟ
static/           style.css, plotly.min.js (Plotly แบบ local ไม่พึ่ง CDN)
tests/            test_dc_bias.py, test_spice_engine.py, test_web.py
docs/             validation.md, design-note.md, reflection.md
```

---

## ข้อจำกัด

- โหมด `spice_*` ใช้เฉพาะวงจร Voltage Divider อ้างอิง และค่าที่ส่งเข้าเป็น
 แบบจำลอง BJT ที่กำหนดไว้ใน netlist (ไม่ได้อ่าน β/VBE จากฟอร์มเพื่อสร้าง model ใหม่)
- ผล `.op` กับผล analytical ต่างกันเล็กน้อยตามแบบจำลองทรานซิสเตอร์ — เป็นเรื่องปกติ
- ถ้า ngspice ไม่มี/ล้มเหลว/หมดเวลา เว็บจะแสดง **Error** และไม่แสดงกราฟเก่า
- Fixed Bias และ Emitter Bias ไม่มี VTH/RTH (แสดงเฉพาะ Divider เท่านั้น)
