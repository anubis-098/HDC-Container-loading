export type Photo = {
  id: string;
  pallet_id: string | null;
  side: string | null;
  byte_size: number;
  archived_at: string | null;
};
export type Pallet = { id: string; number: number; store_code: string; store_name: string; orders: string[]; photos: Photo[] };
export type Shipment = {
  id: string;
  number: string;
  store_code: string;
  store_name: string;
  pallets: Pallet[];
};
export type Trip = {
  id: string;
  truck_id: string;
  truck_province: string | null;
  truck_type: string;
  status: "OPEN" | "DONE" | "CANCELLED";
  created_at: string;
  worker_name?: string;
  shipments: Shipment[];
  structure_version: number;
  pallets: Pallet[];
  photos: Photo[];
};
export type Store = { code: string; name: string; active: boolean; memberships?: { group: string; category: string }[] };
export type Identity = { id: string; name: string; role: string };
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.body instanceof FormData ? 90000 : 30000);
  const abort = () => controller.abort();
  if (options.signal?.aborted) controller.abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  try {
    const response = await fetch("/api" + path, {
        ...options, headers, signal: controller.signal, credentials: "same-origin",
      });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new ApiError(response.status, typeof body.detail === "string"
        ? body.detail : `ทำรายการไม่สำเร็จ (${response.status}) กรุณาตรวจข้อมูล`);
    }
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, controller.signal.aborted
      ? "หมดเวลารอ กรุณาตรวจสอบสถานะแล้วลองใหม่ ข้อมูลอาจบันทึกสำเร็จแล้ว"
      : "เชื่อมต่อไม่ได้ กรุณาตรวจสัญญาณอินเทอร์เน็ตแล้วลองใหม่");
  } finally {
    clearTimeout(timeout);
    options.signal?.removeEventListener("abort", abort);
  }
}
export function message(error: unknown) {
  return error instanceof Error ? error.message : "เกิดข้อผิดพลาด กรุณาลองใหม่";
}
export function uid() {
  if (typeof globalThis.crypto?.randomUUID === "function")
    return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  return [...bytes]
    .map(
      (n, i) =>
        ([4, 6, 8, 10].includes(i) ? "-" : "") +
        n.toString(16).padStart(2, "0"),
    )
    .join("");
}
export function saved(key: string) {
  try {
    return localStorage.getItem(key) || "";
  } catch {
    return "";
  }
}
export function remember(key: string, value: string) {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* Server remains authoritative. */
  }
}
export const sides = [
  { key: "front", label: "ด้านหน้า" },
  { key: "back", label: "ด้านหลัง" },
  { key: "left", label: "ด้านซ้าย" },
  { key: "right", label: "ด้านขวา" },
];

export const truckTypes = [
  "4 ล้อ",
  "6 ล้อ",
  "10 ล้อ",
  "Dock Tailer",
  "18 ล้อ",
  "รถเทรลเลอร์",
] as const;
export const MAX_TRIP_PHOTOS = 120;
