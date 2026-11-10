# BJT DC Bias Web App

เว็บแอป Flask สำหรับคำนวณ **จุดทำงานกระแสตรง (DC Operating Point)** ของทรานซิสเตอร์
BJT แบบ NPN ในวงจร **Common Emitter · Voltage-Divider Bias**

ผลลัพธ์คำนวณด้วย Python ฝั่งเซิร์ฟเวอร์ ไม่ใช่ค่าที่ฝังไว้ใน HTML

---

## แบบจำลองที่ใช้

Forward-Active Approximation โดยถือว่า **β คงที่** และ **V<sub>BE</sub> คงที่**
ไม่ใช่การจำลองแบบ SPICE และไม่แก้วงจรซ้ำ (iterative solve)

```
VTH = VCC × R2 / (R1 + R2)
RTH = R1 × R2 / (R1 + R2)
IB  = (VTH − VBE) / (RTH + (β + 1) × RE)
IC  = β × IB
IE  = (β + 1) × IB
VE  = IE × RE
VB  = VE + VBE
VC  = VCC − IC × RC
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

> ⚠️ **ห้ามเปิด `templates/index.html` ด้วยการ double-click**
> ไฟล์นั้นเป็นเพียง Jinja template ที่เซิร์ฟเวอร์นำไป render
> ถ้าเปิดด้วย `file://` จะไม่มี Python ทำงานและไม่มีผลลัพธ์ใด ๆ

---

## รันเทสต์

```bash
python -m unittest discover -s tests -v
```

ต้องได้ `Ran 19 tests ... OK`

---

## หน่วยของข้อมูลนำเข้า

| ช่อง | ความหมาย | หน่วย |
|---|---|---|
| VCC | แรงดันเลี้ยงวงจร | V |
| R1 | ตัวต้านทาน VCC–Base | **kΩ** |
| R2 | ตัวต้านทาน Base–Ground | **kΩ** |
| RC | ตัวต้านทาน VCC–Collector | **kΩ** |
| RE | ตัวต้านทาน Emitter–Ground | **kΩ** |
| β | อัตราขยายกระแส (hFE) | ไม่มี単位 |
| VBE | แรงดันตกคร่อมรอยต่อเบส–อีมิเตอร์ | V |

ค่าตัวอย่างจากใบงาน: VCC=12, R1=100, R2=22, RC=2.2, RE=1, β=100, VBE=0.70

---

## กฎการแบ่งช่วงการทำงาน

| เงื่อนไข | Region | สิ่งที่เว็บแสดง |
|---|---|---|
| `VTH ≤ VBE` | `CUTOFF` | IB=IC=IE=0, VB=VTH, VC=VCE=VCC + คำเตือน |
| `VCE < 0.3 V` | `SATURATION` | แสดงตัวเลขตามสมการ แต่เตือนว่าแบบจำลองใช้ไม่ได้ |
| `0.3 ≤ VCE < 0.7 V` | `ACTIVE` | แสดงตัวเลข + เตือนว่าใกล้จุดอิ่มตัว |
| `VCE ≥ 0.7 V` | `ACTIVE` | แสดงตัวเลขปกติ |

**เหตุผลที่ต้องมีคำเตือน:** สมการข้างต้นตั้งอยู่บนสมมติฐาน Forward-Active
ถ้าทรานซิสเตอร์อิ่มตัวหรือ cutoff สมมติฐานนั้นใช้ไม่ได้ ตัวเลขที่ได้จึงไม่ใช่
คำตอบของวงจรจริง การแสดงผลโดยไม่เตือนเท่ากับรายงานผลผิดว่าเป็นผลที่เชื่อถือได้

---

## โครงสร้างไฟล์

```
app.py            Flask routes, การอ่านฟอร์ม, การแสดง error
dc_bias.py        สมการทางวิศวกรรมล้วน (ไม่รู้จัก Flask หรือ HTML)
templates/        index.html — ฟอร์ม + ผลลัพธ์
static/           style.css
tests/            test_dc_bias.py (คณิต), test_web.py (HTTP)
docs/             design-note, validation, reflection
```

---

## ข้อจำกัด

- รองรับเฉพาะ Voltage-Divider Bias เท่านั้น
- ไม่มีการวิเคราะห์ AC, Bode plot, transient หรือ DC load line
- ไม่ได้ตรวจสอบกับ ngspice — เป็นแบบจำลองเชิงวิเคราะห์
- Flask debug server ใช้สำหรับพัฒนาเท่านั้น ไม่ควรเปิดสู่เครือข่ายสาธารณะ
