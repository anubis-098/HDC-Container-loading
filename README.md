# CJ Logistics · Container Loading

รุ่นปัจจุบันหลัง UAT: **Trip → หลาย Pallet → หลาย Order ต่อ Pallet** ทุก Pallet ระบุ Store ของตัวเอง มีทั้งภาพรวม Trip และภาพแยก Pallet รวมสูงสุด 120 ภาพ ดูรายละเอียดและการรักษาข้อมูลเก่าใน [Pallet / Order upgrade](docs/pallet-order-upgrade.md)


React + TypeScript + FastAPI + PostgreSQL แยกฐานข้อมูลทั่วไปและภาพ
โครงสร้างใหม่: **Trip → Pallet → Orders / Store** และ **Trip → Photos** (ภาพระบุ Pallet ได้) ข้อมูล Shipment เดิมยังเก็บไว้สำหรับงานเก่า

## เริ่มระบบบน Windows 11 Pro

ต้องมี Docker Desktop (Linux containers / WSL 2)

1. ถ้ายังไม่มี `.env` ให้คัดลอก `.env.example` เป็น `.env` แล้วกำหนดรหัสผ่านฐานข้อมูลสองค่า ไม่ทับ `.env` เดิมที่ใช้งานอยู่
2. รันจากโฟลเดอร์โปรเจกต์:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

API จะรัน SQL migrations แบบมี version ก่อนเปิดบริการ ไม่ลบข้อมูลเดิม
เปิด `https://10.84.185.1:8080` หลังเตรียม Certificate และตั้งค่า `.env` ตามหัวข้อ HTTPS deployment

3. สร้าง Administrator ครั้งแรก (กรอกบัญชีและรหัสผ่านอย่างน้อย 12 ตัว):

```powershell
docker compose exec api python -m app.manage create-admin
```

4. เปิด `/admin/login` เข้าระบบ → เมนู Store → เพิ่ม Store ปลายทาง
5. กลับหน้า `/` กรอกชื่อ–นามสกุล → เริ่ม Trip ด้วยข้อมูลรถ → เพิ่ม Pallet / Store / เลข Order → ถ่ายภาพรวมรถและภาพ Pallet → ยืนยันปิดงาน

## สิ่งที่ใช้งานได้ในโค้ดชุดนี้

- หน้าแรกและหน้าทำงานแบบ Handheld อ้างอิงโครงสร้าง `example_index.html`: แบรนด์/นาฬิกา การ์ดชื่อ ปุ่ม Admin ส่วนข้อมูลรถ ส่วนถ่ายภาพ และแถบปิดงานด้านล่าง
- Session พนักงานไม่ใช้รหัสผ่านตามต้นแบบ (ชื่อเป็นการระบุตนเอง ไม่ใช่การยืนยันตัวบุคคล)
- Session Admin ใช้รหัสผ่าน scrypt, cookie HttpOnly, ตรวจสิทธิ์ที่ API และป้องกัน cross-origin mutation
- เที่ยวรถ/Pallet/Order บันทึก PostgreSQL จริง หนึ่ง Trip มีหลาย Store ผ่าน Pallet แต่ละรายการ พร้อมภาพสองระดับ
- เลข Shipment ไม่ซ้ำทั้งระบบ; คำขอสร้างเดิมใช้ UUID เดิมเพื่อรองรับการส่งซ้ำ
- ภาพถูกบีบอัด ตรวจและแปลงเป็น JPEG ที่ Backend; binary อยู่ PostgreSQL อีกฐาน
- IndexedDB เก็บภาพก่อนส่ง ส่งซ้ำเมื่อกลับออนไลน์/กด retry; รีเฟรชแล้วกลับมาทำต่อผ่านงานค้าง
- Trip ใหม่ปิดงานได้เมื่อมี Pallet อย่างน้อยหนึ่งรายการและภาพอย่างน้อยหนึ่งภาพ ส่งคิวภาพให้ครบก่อนยืนยัน ตรวจข้อมูลฝั่งเซิร์ฟเวอร์ด้วย งานเก่าใช้กติกาเดิม
- Dashboard/ค้นหา/ดูหลักฐาน/CSV ของหน้าปัจจุบัน/จัดการ Store
- Archive พร้อมตรวจ checksum ก่อนลบต้นทาง; ข้อมูลธุรกิจยังอยู่

## ขอบเขตและการใช้งาน

- Backend API และ Docker build ยังไม่ได้รันทดสอบในสภาพแวดล้อมที่แก้โค้ด เนื่องจากไม่มี Python/Docker และ registry npm เข้าไม่ผ่าน จึงต้องรันชุดทดสอบด้านล่างก่อนใช้ข้อมูลจริง
- เว็บ Production ที่ให้มาเข้าถึงจากเครื่องมือไม่ได้ จึงใช้ไฟล์ตัวอย่างในโปรเจกต์อ้างอิงการจัดวาง ยังไม่ได้ยืนยันความเหมือนจากภาพหน้าจอเว็บจริง
- คิวภาพอยู่ใน browser/device เดิม อย่าล้างข้อมูลเว็บไซต์ก่อนส่งภาพครบ; การเปิดเว็บใหม่ขณะออฟไลน์ทั้งหมดไม่รองรับ (ยังไม่มี service worker)
- ต้องออนไลน์ตอนเริ่มงาน/เพิ่ม Shipment/Pallet; ถ้าหน้าเปิดอยู่แล้วและเน็ตหลุด ยังเก็บภาพรอส่งได้
- Session พนักงานอยู่ได้ 30 วัน; ไม่เปลี่ยนชื่อขณะมีงานค้าง เพื่อรักษาทางกลับเข้างานเดิม
- งานปิดแล้วแก้ภาพไม่ได้; UI แก้ข้อมูลรถ/Shipment หลังสร้างและการยกเลิกงานยังไม่ได้เพิ่ม ควรตรวจฟอร์มก่อนบันทึก
- ยังไม่มีเครื่องมือย้ายข้อมูล Firebase, กล้องสแกน barcode, ระบบสร้าง Admin ผ่านหน้าเว็บ
- การสแกนใช้ Zebra DataWedge แบบ keyboard output ลง input; ต้องทดสอบการตั้งค่าบนอุปกรณ์จริง

## HTTPS ก่อนใช้ Handheld จริง

HTTP localhost ใช้สำหรับ Dev เท่านั้น ตั้ง reverse proxy พร้อม certificate ที่ Chrome บน TC22 เชื่อถือก่อนเปิดใช้จริง
ตั้ง `COOKIE_SECURE=true` เมื่อเปิดผ่าน HTTPS แล้วเท่านั้น มิฉะนั้น cookie จะไม่ส่งใน HTTP
ตัวอย่าง Caddy อยู่ใน `deploy/` และ `compose.https.yaml`; ใช้โดเมนที่ควบคุมและ DNS ชี้เซิร์ฟเวอร์

## Storage / Archive

Dev ใช้ Docker named volumes บน SSD เดียว; `.env` ตั้ง `IMAGE_DATA_PATH` และ `ARCHIVE_PATH` ตอน deploy ได้
**การเปลี่ยน path ไม่ได้ย้ายข้อมูลเก่า** ต้องเตรียม storage และย้ายฐานข้อมูลอย่างถูกต้องก่อนเปลี่ยน
ภาพใน PostgreSQL บน Windows/WSL ควรใช้ Linux-backed storage; Archive สามารถ bind mount โฟลเดอร์ Windows ได้
หน้า Admin Settings แสดงจำนวนภาพ ขนาดข้อมูล และสถานะ Archive จริง; ตัวเลือกย้าย Storage Profile จาก UI ยังไม่เปิดใช้

ค่าเริ่มต้น `ARCHIVE_ENABLED=false` เพื่อให้ผู้ติดตั้งกำหนดและตรวจปลายทางก่อน
เมื่อตั้งปลายทางพร้อม ให้กำหนด `ARCHIVE_ENABLED=true`, `PHOTO_RETENTION_DAYS=30` แล้วรัน Compose ใหม่
Worker ตรวจทุก 24 ชั่วโมงตั้งแต่เริ่มทำงาน เก็บภาพของเที่ยวรถ DONE ที่อายุเกิน 30 วันลง ZIP พร้อม manifest/checksum ก่อนลบ binary ต้นทาง
ยังไม่ลบ archive อัตโนมัติ ภาพที่ archive แล้วเปิดดูจากหน้า Admin ได้โดยตรวจ checksum ของ Archive ก่อนส่งกลับ
Backup ฐานข้อมูลทั่วไป ฐานข้อมูลภาพ และ Archive แยกกัน และมีสำเนานอกเครื่อง
ไม่ใช้ `docker compose down -v` กับข้อมูลที่ต้องเก็บ

## ทดสอบแบบแยกข้อมูลจากระบบจริง

```powershell
docker compose -p loading-tests -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -p loading-tests -f compose.test.yaml down
```

ชุดทดสอบใช้ฐานข้อมูล test แบบ tmpfs แยก network ไม่มี volume ร่วมกับระบบจริง
ครอบคลุม workflow 4 ด้าน, ส่งซ้ำ, สิทธิ์ข้ามพนักงาน, รหัสผ่าน, CSRF, login rate limit, ภาพผิดรูปแบบ, blob หาย และ Archive

ตรวจ logs:

```powershell
docker compose logs --tail 100 api frontend archive-worker
```

## โครงสร้างไฟล์

- `frontend/src/features/client/`: หน้าเข้าระบบพนักงานและหน้าทำงาน Handheld
- `frontend/src/pages/`: Dashboard, Store, หลักฐาน, Settings, Admin Login
- `frontend/src/lib/`: API client และ IndexedDB photo queue
- `frontend/src/components/`: Clock, PhotoTile, shadcn-style UI components
- `backend/app/api/`: endpoints และ validation
- `backend/app/core/`: configuration, authentication และ authorization
- `backend/app/db/`: connection แยกสองฐาน
- `backend/app/services/`: ตรวจ/แปลงภาพ
- `backend/app/workers/`: archive และ scheduler
- `backend/migrations/app/`, `backend/migrations/images/`: SQL migrations แยกประวัติ version
- `backend/tests/`: integration tests


### Admin: ภาพและรายงาน Trip

- คลิกภาพเพื่อขยาย ซูม 100–400% และเลื่อนดูภาพก่อนหน้า/ถัดไป
- ดาวน์โหลด JPG รายภาพ หรือ ZIP รวมภาพทั้งหมด รวมภาพที่ Archive แล้ว
- ปุ่มรายงาน PDF: A4 แนวนอน 6 ภาพต่อหน้า พร้อม CI CJ Logistics ข้อมูล Trip / Shipment / Store และเลขหน้า
- PDF ย่อภาพไม่เกิน 1200 px และ JPEG quality 78 โดยไม่เปลี่ยนไฟล์ต้นฉบับ; 120 ภาพใช้ 20 หน้า
- ต้อง rebuild ทั้ง api และ frontend เพื่อเพิ่ม ReportLab และฟอนต์ภาษาไทย: `docker compose up -d --build`
- Integration test ครอบคลุมสิทธิ์ Admin, ภาพ Archive, ZIP, จำนวนหน้า/ขนาด PDF และกรณีข้อมูลภาพหาย ผ่าน Compose test เดิม

### จังหวัดป้ายทะเบียน
- ช่องทะเบียนรถและจังหวัดแบ่งเป็นสองคอลัมน์; พิมพ์จังหวัดตั้งแต่ 2 ตัวอักษรเพื่อกรองและเลือกเติมชื่ออัตโนมัติ รองรับการแตะและปุ่มลูกศร/Enter/Escape
- Migration `004_truck_province.sql` สร้างตาราง `provinces` ในฐานข้อมูลหลัก พร้อม 77 รายการ (รวมกรุงเทพมหานครและบึงกาฬ) และ `trips.truck_province` เป็น foreign key
- Trip เก่าคงค่า NULL; API ยอมรับการไม่ส่งจังหวัดเพื่อรองรับ Client รุ่นก่อน แต่ฟอร์มใหม่บังคับเลือกจังหวัดที่ถูกต้อง
- อัปเดตด้วย `docker compose up -d --build` เพื่อให้ API เรียก migration อัตโนมัติ


## HTTPS deployment

The frontend now serves HTTPS on its existing host port. Before starting Compose,
place `hdc-server.crt` and `hdc-server.key` in `D:/HDC-Certificates` on the Docker
host. Set `HDC_TLS_DIRECTORY` in `.env` only if using a different directory.
The certificate must include the server IP in its IP Subject Alternative Name,
and client devices must trust its issuing CA.

Set `COOKIE_SECURE=true` in `.env`, then rebuild using the existing Data Center
`scripts/Start-Integration.ps1` workflow to retain shared accounts and Store sync.
Do not recreate database volumes. Port 80 stays internal for health checks;
the published frontend port maps to HTTPS port 443. Import only the root CA's
public `.cer` certificate into the SOTI Certificates profile, then assign it to
the devices. Private keys stay on the server.
