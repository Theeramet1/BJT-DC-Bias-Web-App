# BJT DC Bias Web App (Lab 03)

เว็บแอป Flask สำหรับคำนวณ **จุดทำงานกระแสตรง (DC Operating Point)** ของทรานซิสเตอร์
BJT แบบ NPN ในวงจร Common Emitter รองรับ **สามวงจรไบอัส**: Voltage Divider, Fixed Bias และ Emitter Bias

ผลลัพธ์คำนวณด้วย Python ฝั่งเซิร์ฟเวอร์ ไม่ใช่ค่าที่ฝังไว้ใน HTML

---

## วงจรที่รองรับ

| โหมด | อินพุตเพิ่มเติม | คำอธิบายวงจร |
|------|----------------|--------------|
| Voltage Divider | R1, R2, RE | R1 ต่อจาก VCC ไป Base, R2 ต่อจาก Base ลงกราวด์, RE ต่อจาก Emitter ลงกราวด์ |
| Fixed Bias | RB | RB ต่อจาก VCC ไป Base, Emitter ต่อลงกราวด์โดยตรง |
| Emitter Bias | RB, RE | RB ต่อจาก VCC ไป Base, RE ต่อจาก Emitter ลงกราวด์ |

อินพุตร่วมทุกโหมด: VCC, RC, β, VBE

---

## สมการที่ใช้ (แบบจำลอง Forward-Active, β และ VBE คงที่)

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
- Git (สำหรับ clone)

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

> ⚠️ **ห้ามเปิด `templates/index.html` ด้วยการ double-click**
> ไฟล์นั้นเป็นเพียง Jinja template ที่เซิร์ฟเวอร์นำไป render

---

## รันเทสต์

```bash
python -m unittest discover -s tests -v
```

ต้องได้ `Ran 32 tests ... OK` (12 เทสต์คณิต + 20 เทสต์ HTTP)

---

## หน่วยของข้อมูลนำเข้า

| ช่อง | ความหมาย | หน่วย |
|---|---|---|
| VCC | แรงดันเลี้ยงวงจร | V |
| R1, R2, RB, RC, RE | ตัวต้านทาน | **kΩ** |
| β | อัตราขยายกระแส (hFE) | ไม่มีหน่วย |
| VBE | แรงดันตกคร่อมรอยต่อเบส–อีมิเตอร์ | V |

ค่าตัวอย่างจากใบงาน: VCC=12, RC=2.2, β=100, VBE=0.70

---

## กฎการแบ่งช่วงการทำงาน

| เงื่อนไข | Region | สิ่งที่เว็บแสดง |
|---|---|---|
| `VTH ≤ VBE` (Divider) | `CUTOFF` | IB=IC=IE=0, VB=VTH, VC=VCE=VCC + คำเตือน |
| `VCE < 0.3 V` | `SATURATION` | แสดงตัวเลข แต่เตือนว่าแบบจำลองใช้ไม่ได้ |
| `0.3 ≤ VCE < 0.7 V` | `ACTIVE` | แสดงตัวเลข + เตือนว่าใกล้จุดอิ่มตัว |
| `VCE ≤ 0.2 V` | `ACTIVE` | แสดงตัวเลข + เตือนว่า Forward Active อาจใช้ไม่ได้ |
| `VCE ≥ 0.7 V` | `ACTIVE` | แสดงตัวเลขปกติ |
| `IB ≤ 0` | `ACTIVE` | เตือนว่ากระแสเบสผิดปกติ |

---

## โครงสร้างไฟล์

```
app.py            Flask routes, การอ่านฟอร์ม, การเลือกโหมด, การแสดง error
dc_bias.py        สมการทางวิศวกรรมล้วน (ไม่รู้จัก Flask หรือ HTML)
templates/        index.html — ฟอร์ม + ตัวเลือกโหมด + ผลลัพธ์
static/           style.css
tests/            test_dc_bias.py (คณิต), test_web.py (HTTP)
docs/             validation.md
```

---

## ข้อจำกัด

- รองรับเฉพาะ DC Operating Point เท่านั้น ไม่มี AC, Bode plot, transient หรือ DC Load Line
- ไม่ได้ตรวจสอบกับ ngspice — เป็นแบบจำลองเชิงวิเคราะห์
- Flask debug server ใช้สำหรับพัฒนาเท่านั้น ไม่ควรเปิดสู่เครือข่ายสาธารณะ
- Fixed Bias และ Emitter Bias ไม่มี VTH/RTH (แสดงเฉพาะ Divider เท่านั้น)
