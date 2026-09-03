# คู่มือการสร้างไฟล์ติดตั้ง Windows (Windows Installer Build Guide)

เป้าหมายของ Universal installer:
- **Windows 7 SP1 (32-bit & 64-bit)**
- **Windows 8 & 8.1**
- **Windows 10**
- **Windows 11**

รองรับเครื่องสถาปัตยกรรม Intel/AMD แบบ x86 และ x64; Windows on ARM ไม่อยู่ในขอบเขต release นี้

Windows 7/8/8.1 ต้องมี Universal C Runtime (`KB2999226`) จาก Windows Update แล้ว ตัว Setup จะตรวจสอบก่อนติดตั้ง หากยังไม่มี ให้ติดตั้งจากหน้า [Microsoft Universal C Runtime](https://support.microsoft.com/en-us/servicing/os/windows/2020/04/update-for-universal-c-runtime-in-windows) และรีสตาร์ตเครื่องก่อน เนื่องจาก Python 3.8 และ Windows 7 หมดระยะสนับสนุน การรองรับ Windows 7 จึงเป็น compatibility mode และต้องผ่านการทดสอบบนเครื่องจริงหรือ VM ก่อนเรียกไฟล์ว่า release

---

## 🚀 วิธีที่ 1: สั่ง Build บนคลาวด์อัตโนมัติ (ไม่ต้องใช้เครื่อง Windows) *[แนะนำ]*

หากคุณทำงานบน Mac และไม่มีเครื่อง Windows ในตอนนี้ สามารถใช้ระบบ **GitHub Actions** ที่สร้างไว้ให้คอมไพล์เป็นไฟล์ติดตั้งบนคลาวด์ได้ฟรี:

1. นำโฟลเดอร์โปรเจกต์นี้ขึ้น GitHub Repository (เช่น `git push origin main`)
2. เข้าไปที่แท็บ **Actions** บน GitHub
3. เลือก Workflow **"Build Universal Windows Installer"**
4. คลิกปุ่ม **"Run workflow"**
5. ดาวน์โหลด Artifact `Setup_BatteryRequisition_v1.0.0_Installer`
6. ภายในจะมี `BatteryRequisition_Setup_v1.0.0.exe` ซึ่งเลือก x86/x64 ให้อัตโนมัติ

Workflow ยังสร้าง ZIP แบบพกพาแยก x86 และ x64 สำหรับการวิเคราะห์ปัญหา

---

## 💻 วิธีที่ 2: สั่ง Build ใน 1 คลิก บนเครื่อง Windows (Local Build)

หากคุณมีเครื่องคอมพิวเตอร์ Windows หรือเครื่องเพื่อน:

### สิ่งที่ต้องมีในเครื่อง Windows:
1. **Python 3.8.10 ทั้งแบบ 32-bit และ 64-bit**
   - ดาวน์โหลด: https://www.python.org/downloads/release/python-3810/
   - *ข้อสำคัญ:* ตอนติดตั้ง ให้ติ๊กถูกหน้า **"Add Python to PATH"**
2. **Inno Setup 6.7.1:** สำหรับสร้าง Universal Setup
   - ดาวน์โหลด: https://jrsoftware.org/isdl.php

### ขั้นตอนการสร้างไฟล์:
1. ก๊อปปี้โฟลเดอร์โปรเจกต์นี้ไปไว้ที่เครื่อง Windows
2. ดับเบิลคลิกที่ไฟล์ **`build_windows.bat`**
3. ระบบจะสร้าง virtual environment แยก x86/x64 ติดตั้ง dependency ที่ล็อกเวอร์ชันไว้ รัน self-test และเรียก Inno Setup
4. เมื่อเสร็จสิ้น จะได้ไฟล์ติดตั้งอยู่ที่:
   - **`dist_installer\BatteryRequisition_Setup_v1.0.0.exe`**

---

## 🛡️ ความปลอดภัยของข้อมูลเมื่อมีการติดตั้งเวอร์ชันใหม่ในอนาคต

- ฐานข้อมูลอยู่ที่ `%LOCALAPPDATA%\BatteryRequisition\inventory.db`
- PDF อยู่ที่ Documents `BatteryRequisition\PDF`
- รายงาน Excel อยู่ที่ Documents `BatteryRequisition\Reports`
- Setup ไม่ติดตั้งและไม่ถอนข้อมูลใน `%LOCALAPPDATA%`
- โปรแกรมสำรองข้อมูลวันละครั้ง 30 ชุด และก่อนอัปเดต 10 ชุด
- เมนูตั้งค่ามีปุ่มส่งออกและกู้คืนฐานข้อมูล โดยตรวจสอบไฟล์ก่อนแทนที่

## เกณฑ์ก่อนแจกใช้งาน

GitHub Actions ตรวจ build และ smoke-test บน Windows Server 2022 เท่านั้น ก่อนประกาศเป็น release ต้องทดสอบอย่างน้อย:

- Windows 7 SP1 x86
- Windows 7 SP1 x64
- Windows 10 x64
- Windows 11 x64

ในแต่ละเครื่องให้ทดสอบติดตั้ง เปิดโปรแกรม เพิ่ม/เบิกสินค้า สร้าง PDF ภาษาไทย ส่งออก Excel ติดตั้งอัปเดตทับ ถอนโปรแกรม และยืนยันว่า DB ยังอยู่
