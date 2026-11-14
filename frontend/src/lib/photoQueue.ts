import { uid } from "./api";
export type PendingPhoto = {
  key: string;
  version: string;
  tripId: string;
  photoId?: string;
  palletId?: string;
  side?: string;
  blob: Blob;
};
function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("cj-loading-photos", 1);
    request.onupgradeneeded = () =>
      request.result.createObjectStore("queue", { keyPath: "key" });
    request.onsuccess = () => resolve(request.result);
    request.onerror = () =>
      reject(
        new Error(
          "เปิดที่เก็บภาพในเครื่องไม่ได้ กรุณาอนุญาตพื้นที่เก็บข้อมูลของเว็บไซต์",
        ),
      );
  });
}
export async function allPending(): Promise<PendingPhoto[]> {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("queue", "readonly");
    const request = tx.objectStore("queue").getAll();
    tx.oncomplete = () => {
      db.close();
      resolve(request.result);
    };
    tx.onerror = () => {
      db.close();
      reject(new Error("อ่านคิวภาพไม่สำเร็จ"));
    };
  });
}
export async function enqueue(tripId: string, blob: Blob) {
  const db = await database();
  const photoId = uid();
  const item: PendingPhoto = {
    key: photoId,
    version: uid(),
    tripId,
    photoId,
    blob,
  };
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction("queue", "readwrite");
    tx.objectStore("queue").put(item);
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(
        new Error(
          "พื้นที่เก็บภาพในเครื่องไม่พอ ภาพยังไม่ถูกบันทึก กรุณาลองใหม่",
        ),
      );
    };
  });
}
export async function acknowledge(item: PendingPhoto) {
  const db = await database();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction("queue", "readwrite");
    const store = tx.objectStore("queue");
    const request = store.get(item.key);
    request.onsuccess = () => {
      if (request.result?.version === item.version) store.delete(item.key);
    };
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(new Error("ปรับปรุงคิวภาพไม่สำเร็จ"));
    };
  });
}
export async function compress(file: File): Promise<Blob> {
  if (
    !["image/jpeg", "image/png", "image/webp"].includes(file.type) ||
    file.size > 20 * 1024 * 1024
  )
    throw new Error("รองรับ JPEG, PNG, WebP ขนาดไม่เกิน 20 MB");
  const url = URL.createObjectURL(file);
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error("อ่านภาพไม่สำเร็จ"));
      img.src = url;
    });
    const scale = Math.min(
      1,
      1600 / Math.max(image.naturalWidth, image.naturalHeight),
    );
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(image.naturalWidth * scale);
    canvas.height = Math.round(image.naturalHeight * scale);
    const ctx = canvas.getContext("2d");
    if (!ctx) throw new Error("ไม่สามารถเตรียมภาพได้");
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    return await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob(
        (blob) =>
          blob ? resolve(blob) : reject(new Error("บีบอัดภาพไม่สำเร็จ")),
        "image/jpeg",
        0.82,
      ),
    );
  } finally {
    URL.revokeObjectURL(url);
  }
}
