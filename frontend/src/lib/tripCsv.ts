import type { Trip } from "./api";

export function tripCsv(trips: Trip[]): string {
  const dateFormat = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Bangkok", year: "numeric", month: "2-digit", day: "2-digit",
  });
  const timeFormat = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Bangkok", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  });
  const lines: unknown[][] = [[
    "ทะเบียนรถ", "จังหวัดป้ายทะเบียน", "ประเภทรถ", "ผู้บันทึก", "สถานะ",
    "วันที่สร้าง", "เวลาสร้าง (ประเทศไทย)", "Pallet", "รหัส Store", "ชื่อ Store", "เลข Order",
    "Shipment (เดิม)", "จำนวน Pallet ทั้งเที่ยว", "จำนวนภาพทั้งเที่ยว",
  ]];
  for (const trip of trips) {
    const created = new Date(trip.created_at);
    const base = [trip.truck_id, trip.truck_province, trip.truck_type,
      trip.worker_name, trip.status, dateFormat.format(created), timeFormat.format(created)];
    const totals = [trip.pallets.length, trip.photos.length];
    if (trip.pallets.length) {
      for (const pallet of trip.pallets) {
        const shipment = trip.shipments.find(item => item.pallets.some(p => p.id === pallet.id));
        for (const order of pallet.orders.length ? pallet.orders : [""]) {
          lines.push([...base, pallet.number, pallet.store_code, pallet.store_name, order, shipment?.number, ...totals]);
        }
      }
    } else {
      for (const shipment of trip.shipments.length ? trip.shipments : [null]) {
        lines.push([...base, "", shipment?.store_code, shipment?.store_name, "", shipment?.number, ...totals]);
      }
    }
  }
  const cell = (value: unknown) => '"' + String(value ?? "")
    .replace(/^[\s\u0000-\u001f]*[=+@-]/, "'$&").replaceAll('"', '""') + '"';
  return "\ufeff" + lines.map(line => line.map(cell).join(",")).join("\r\n");
}
