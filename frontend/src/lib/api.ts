export type Photo = {
  id: string;
  side: string | null;
  byte_size: number;
  archived_at: string | null;
};
export type Pallet = { id: string; number: number; photos: Photo[] };
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
  status: "OPEN" | "DONE";
  created_at: string;
  worker_name?: string;
  shipments: Shipment[];
  photos: Photo[];
};
export type Store = { code: string; name: string; active: boolean };
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
  let response: Response;
  try {
    response = await fetch("/api" + path, {
      ...options,
      headers,
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(
      0,
      "เชื่อมต่อไม่ได้ กรุณาตรวจสัญญาณอินเทอร์เน็ตแล้วลองใหม่",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      typeof body.detail === "string"
        ? body.detail
        : `ทำรายการไม่สำเร็จ (${response.status}) กรุณาตรวจข้อมูล`,
    );
  }
  return response.json() as Promise<T>;
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
  "8 ล้อ",
  "12 ล้อ",
  "เทรลเลอร์",
] as const;
export const MAX_TRIP_PHOTOS = 120;
