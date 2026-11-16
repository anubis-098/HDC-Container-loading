import { t, useLanguage, locale } from "../lib/i18n";
import { useEffect, useState } from "react";
import { HardDrive, ShieldCheck } from "lucide-react";
import { api, message } from "../lib/api";
type StorageStatus = {
  online_photos: number;
  archived_photos: number;
  online_bytes: number;
  retention_days: number;
  archive_enabled: boolean;
  archive_free_bytes: number | null;
};
export function SettingsPage() {
  useLanguage();
  const [status, setStatus] = useState<StorageStatus | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<StorageStatus>("/admin/storage")
      .then(setStatus)
      .catch((error) => setError(message(error)));
  }, []);
  return (
    <section>
      <h1>{t("ตั้งค่าระบบ")}</h1>
      <p>Windows 11 Pro · Docker / WSL 2</p>
      {error && (
        <p className="error-box" role="alert">
          {t(error)}
        </p>
      )}
      <div className="panel">
        <h2 className="flex items-center gap-2">
          <HardDrive size={22} />
          {t("พื้นที่เก็บภาพ")}
        </h2>
        <p>{t("ฐานข้อมูลทั่วไปและฐานข้อมูลภาพแยกกัน")}</p>
        {status && (
          <p>
            {t("ภาพออนไลน์")}
            {status.online_photos}
            {t("ภาพ · ขนาดภาพรวม")}{" "}
            {(Number(status.online_bytes) / 1024 / 1024).toFixed(1)} MB
          </p>
        )}
        <p className="client-hint">
          {t(
            "พื้นที่ใช้งานตามการติดตั้ง Docker ของเซิร์ฟเวอร์ การย้าย Storage Profile ผ่านหน้าจอยังไม่เปิดใช้งาน",
          )}
        </p>
      </div>
      <div className="panel">
        <h2 className="flex items-center gap-2">
          <ShieldCheck size={22} />
          {t("Archive และการเก็บรักษา")}
        </h2>
        {status ? (
          <>
            <p>
              {t("เก็บภาพออนไลน์")}
              {status.retention_days}
              {t("วัน · Archive แล้ว")} {status.archived_photos}
              {t("ภาพ")}
            </p>
            <p>
              {t("งาน Archive อัตโนมัติ:")}{" "}
              {status.archive_enabled
                ? t("เปิดใช้งาน (ตรวจทุก 24 ชั่วโมง)")
                : t("ปิด — ให้ผู้ติดตั้งเตรียมพื้นที่ Archive และเปิดใช้งาน")}
            </p>
            <p>
              {t("พื้นที่ว่างของปลายทาง Archive:")}{" "}
              {status.archive_free_bytes === null
                ? t("ตรวจสอบไม่ได้")
                : (status.archive_free_bytes / 1024 ** 3).toFixed(1) + " GB"}
            </p>
            <p className="client-hint">
              {t(
                "Archive เฉพาะภาพของเที่ยวรถที่ปิดแล้ว ตรวจ checksum ก่อนลบภาพต้นทาง โดยยังเก็บข้อมูลเที่ยวรถไว้",
              )}
            </p>
          </>
        ) : (
          <p>
            {error
              ? t("โหลดสถานะไม่สำเร็จ กรุณาตรวจการเชื่อมต่อแล้วรีเฟรชหน้า")
              : t("กำลังโหลดสถานะ…")}
          </p>
        )}
      </div>
    </section>
  );
}
