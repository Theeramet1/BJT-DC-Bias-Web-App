# Design Note — BJT DC Bias Web App

**ENG29 2121 · Lab 02 · 2/2569**

## เป้าหมาย

สร้างเว็บแอป Flask ที่รับค่าอุปกรณ์ของวงจร Voltage-Divider Bias แล้วคำนวณ
DC Operating Point ด้วย Python ฝั่งเซิร์ฟเวอร์ พร้อมตรวจสอบข้อมูลนำเข้าและ
เตือนเมื่อผลอยู่นอกขอบเขตที่แบบจำลองใช้ได้

จุดสำคัญของโจทย์ไม่ใช่การคำนวณ แต่คือการแสดงว่า **เว็บเพจที่มี Python Backend
ไม่เหมือนไฟล์ HTML ที่เปิดด้วย `file://`** — ตัวเลขต้องเดินทางจากฟอร์ม →
HTTP Request → Python → HTTP Response → เบราว์เซอร์

## ขอบเขต

**ทำ**

- วงจรเดียว: NPN Common Emitter, Voltage-Divider Bias
- แบบจำลอง Forward-Active Approximation (β คงที่, V<sub>BE</sub> คงที่)
- ฟอร์มรับ VCC, R1, R2, RC, RE, β, VBE
- แสดง VB, VE, VC, VCE, IC, IB, IE พร้อมหน่วย
- Validation และ Region Warning
- Automated tests และ README

**ไม่ทำ**

- AC small-signal, gain, Bode plot
- Transient, signal generator
- SPICE / ngspice, DC load line
- Bias แบบอื่น (fixed bias, emitter bias)
- FET, interactive schematic, ฐานข้อมูล, authentication

## สถาปัตยกรรม

เลือกแบบ **แยก route**: `GET /` สำหรับฟอร์ม และ `POST /calculate` สำหรับคำนวณ

เหตุผล: ทำให้ A1 (หน้าแรกขึ้น) และ A2 (คำนวณถูก) ทดสอบแยกจากกันได้
ถ้าส่วนคำนวณพัง หน้าแรกยังผ่าน และรู้ทันทีว่าพังที่ไหน

ทางเลือกที่ตัดออก: หน้าเดียว `POST /` (ทดสอบแยกไม่ได้),
JSON API + `fetch()` (ใบงานกำหนดให้ Python render HTML และ JS
เพิ่มจุดพังที่ต้อง debug ภายในเวลาจำกัด)

## การแบ่งความรับผิดชอบ

| ไฟล์ | หน้าที่ |
|---|---|
| `dc_bias.py` | สมการล้วน ไม่รู้จัก HTTP/HTML คืน `BiasResult` |
| `app.py` | อ่านฟอร์ม แปลงชนิดข้อมูล จัดการ error เลือก template |
| `templates/index.html` | แสดงผลเท่านั้น ไม่มีสมการ |
| `static/style.css` | หน้าตา |
| `tests/` | แยกเทสต์คณิตกับเทสต์ HTTP |

## สมการ

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

## กฎการแบ่งช่วง

| เงื่อนไข | Region | พฤติกรรม |
|---|---|---|
| `VTH ≤ VBE` | `CUTOFF` | IB=IC=IE=0, VE=0, VB=VTH, VC=VCE=VCC, มีคำเตือน |
| `VCE < 0.3 V` | `SATURATION` | แสดงตัวเลขตามสมการ แต่เตือนว่าใช้ไม่ได้ |
| `0.3 ≤ VCE < 0.7 V` | `ACTIVE` | แสดงตัวเลข + เตือนใกล้จุดอิ่มตัว |
| `VCE ≥ 0.7 V` | `ACTIVE` | แสดงตัวเลขปกติ |

ในกรณี CUTOFF ใช้ `VB = VTH` เพราะเมื่อกระแสเบสเป็นศูนย์ ตัวแบ่งแรงดันเป็น
ตัวกำหนดแรงดันที่ขาเบสโดยตรง (ถ้าใช้ `VB = VBE` จะขัดกับเงื่อนไข cutoff เอง)

## Validation

| เงื่อนไข | ข้อความ |
|---|---|
| ว่าง | กรุณากรอกค่านี้ |
| ไม่ใช่ตัวเลข / `inf` | ต้องเป็นตัวเลข |
| VCC, R, β ≤ 0 | ต้องมากกว่า 0 |
| VBE ≤ 0 หรือ VBE ≥ VCC | ต้องอยู่ระหว่าง 0 ถึง VCC |

ข้อมูลผิดทุกกรณีตอบกลับด้วย **HTTP 200** พร้อมข้อความรายช่อง ค่าที่พิมพ์ไว้
ยังคงอยู่ในฟอร์ม และหน้าเว็บไม่ล้ม
