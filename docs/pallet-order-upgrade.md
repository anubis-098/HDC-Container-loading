# Trip / Pallet / Order หลัง UAT

## ขั้นตอนสำหรับผู้ปฏิบัติงาน

1. ข้อมูลรถ: ทะเบียน ชนิดรถ และจังหวัด (ไม่บังคับ) แล้วกดเริ่มเที่ยวรถ ไม่ต้องกรอก Shipment/Store ในขั้นตอนนี้
2. เพิ่ม Pallet: เลือก Store และกรอก Order อย่างน้อยหนึ่งเลขทุก Pallet เพิ่มเลข Order ได้หลายเลข
3. ถ่ายภาพ: ถ่ายหรือเลือกไฟล์ใน Pallet แต่ละรายการ หมวดภาพรวม Trip แสดงภาพเดิมและสถานะรวม ไม่มีปุ่มเพิ่มภาพ ภาพรวมทั้งเที่ยวรถสูงสุด 120 ภาพ
4. ตรวจสอบ: บันทึกฟอร์ม Pallet ที่เปิดอยู่ ส่งภาพรอส่งให้ครบ แล้วปิดเที่ยวรถ

Trip ใหม่ต้องมี Pallet อย่างน้อยหนึ่งรายการ ทุก Pallet ต้องมีเลข Order และมีภาพอย่างน้อยหนึ่งภาพรวมทุกหมวดก่อนปิด ระบบไม่บังคับภาพครบทุก Pallet เนื่องจากยังไม่ได้กำหนดจำนวนขั้นต่ำต่อ Pallet

Order เดียวกันกระจายอยู่หลาย Pallet ได้ แต่ห้ามซ้ำใน Pallet เดียว เก็บเป็นข้อความเพื่อรักษาเลขศูนย์นำหน้า ไม่เปลี่ยนเลข Shipment เดิมเป็น Order โดยอัตโนมัติ Pallet แบบใหม่ที่สร้างไว้ก่อนบังคับ Order ต้องเพิ่มเลข Order ก่อนปิดงาน ส่วนประวัติงานที่ปิดแล้วคงเดิม

## โครงสร้าง

- `trips.structure_version=2`: Trip ใหม่ที่ใช้ Pallet เป็นรายการสินค้า
- `pallets.trip_id`, `store_code`, `store_name`: แยก Store ต่อ Pallet เก็บ snapshot ชื่อ Store
- `pallet_orders`: หลายเลข Order ต่อ Pallet เรียงตามที่กรอก
- `photos.pallet_id=NULL`: ภาพรวม Trip; ค่า UUID: ภาพของ Pallet นั้น
- ทุกภาพยังมี trip_id เพื่อใช้ authorization, limit, archive และตรวจข้อมูลก่อนปิดงานร่วมกัน

## API

- POST `/api/trips` ส่งข้อมูลรถ ไม่ต้องส่ง shipment_number/store_code
- POST `/api/trips/{id}/pallets` ส่ง `{id,store_code,orders:[]}` ใช้ UUID เดิมเมื่อลองส่งใหม่
- PUT `/api/trips/{id}/pallets/{pallet}` แก้ Store และรายการ Order ขณะ Trip ยังเปิด
- PUT `/api/trips/{id}/photos/{photo}` อัปโหลดภาพรวม หรือเพิ่ม query `pallet_id` สำหรับภาพ Pallet
- GET Trip คืนทั้ง pallets, orders, photos.pallet_id และ legacy shipments
- Admin ค้นหาด้วย Order/Store ใหม่ได้ CSV แสดงจำนวน Pallet; ZIP แบ่งหมวดภาพและมี manifest.json; PDF มีป้ายภาพและหน้ารายละเอียด Pallet/Order

## ข้อมูลเก่า

Migration 006 เพิ่มและ backfill ข้อมูลจาก Shipment เดิม โดยไม่เปลี่ยน UUID, ภาพ, checksum, งาน Archive หรือ Store snapshot ประวัติงานเดิมยังมี legacy Shipment แสดงให้อ้างอิง

Trip เดิมใช้ structure_version=1 และปิดงานตามกติกาเดิมได้ หากเพิ่ม Pallet ใหม่เข้า Trip เดิมที่ยังเปิดอยู่ จะเปลี่ยนเป็นกติกาแบบใหม่ Legacy API และคิวภาพเก่ายังรองรับสำหรับการส่งซ้ำ/ทำงานค้าง

## ทดสอบและ deploy

ใช้ compose.test.yaml ใน project แยก ไม่มี volume ข้อมูลจริง ทดสอบหลาย Store/Orders, รูปสองระดับ, request ID, สิทธิ์เจ้าของ Trip, การปิดงาน, ZIP/PDF และ migration ข้อมูลเก่า

สำรองฐานข้อมูลทั่วไปก่อน deploy จากนั้น rebuild API และ frontend ด้วย Compose overlay เดิมของ Data Center Startup จะรัน migration 006 อัตโนมัติ อย่า rollback API รุ่นเก่าโดยไม่วางแผน เพราะข้อมูล Pallet แบบใหม่ไม่ได้อยู่ใต้ Shipment
