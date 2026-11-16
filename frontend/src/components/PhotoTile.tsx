import { t, useLanguage, locale } from "../lib/i18n";
import { useEffect, useState } from "react";
import { Camera, CheckCircle2, CloudUpload } from "lucide-react";
import type { Photo } from "../lib/api";
import type { PendingPhoto } from "../lib/photoQueue";
export function PhotoTile({
  label,
  photo,
  pending,
  disabled,
  onCapture,
}: {
  label: string;
  photo?: Photo;
  pending?: PendingPhoto;
  disabled: boolean;
  onCapture: (file: File) => void;
}) {
  useLanguage();
  const [local, setLocal] = useState("");
  useEffect(() => {
    if (!pending) {
      setLocal("");
      return;
    }
    const url = URL.createObjectURL(pending.blob);
    setLocal(url);
    return () => URL.revokeObjectURL(url);
  }, [pending]);
  const src =
    local || (photo && !photo.archived_at ? `/api/photos/${photo.id}` : "");
  return (
    <label
      className={`capture-tile ${pending ? "pending" : photo ? "uploaded" : ""}`}
    >
      {src ? (
        <img src={src} alt={label} loading="lazy" />
      ) : (
        <Camera size={28} />
      )}
      <b>{label}</b>
      <span>
        {pending ? (
          <>
            <CloudUpload size={13} />
            {t("รอส่ง")}
          </>
        ) : photo ? (
          <>
            <CheckCircle2 size={13} />{" "}
            {photo.archived_at
              ? t("Archive แล้ว")
              : disabled
                ? t("ส่งสำเร็จ")
                : t("ส่งแล้ว · ถ่ายใหม่")}
          </>
        ) : (
          t("แตะเพื่อถ่ายภาพ")
        )}
      </span>
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        disabled={disabled}
        aria-label={t("ถ่ายภาพ{0}", label)}
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (file) onCapture(file);
        }}
      />
    </label>
  );
}
