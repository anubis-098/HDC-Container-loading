import { t, useLanguage, locale } from "../lib/i18n";
import { useEffect, useRef } from "react";
import { CheckCircle2 } from "lucide-react";
import { Button } from "./ui/button";

export function CloseTripDialog({
  truckId,
  photoCount,
  busy,
  canConfirm,
  error,
  onBack,
  onConfirm,
}: {
  truckId: string;
  photoCount: number;
  busy: boolean;
  canConfirm: boolean;
  error: string;
  onBack: () => void;
  onConfirm: () => void;
}) {
  useLanguage();
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.showModal();
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  return (
    <dialog
      ref={dialog}
      className="close-trip-dialog"
      aria-labelledby="close-trip-title"
      aria-describedby="close-trip-description"
      aria-busy={busy}
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onBack();
      }}
    >
      <div className="close-trip-icon">
        <CheckCircle2 size={28} />
      </div>
      <h2 id="close-trip-title">{t("ยืนยันปิดเที่ยวรถ?")}</h2>
      <p className="close-trip-truck">
        {truckId} · {photoCount}
        {t("ภาพ")}
      </p>
      <p id="close-trip-description">
        {t("หลังปิดงานจะไม่สามารถเพิ่มภาพในเที่ยวรถนี้ได้")}
      </p>
      {error && (
        <p className="error-box" role="alert">
          {t(error)}
        </p>
      )}
      <div className="close-trip-actions">
        <Button
          type="button"
          variant="outline"
          autoFocus
          disabled={busy}
          onClick={onBack}
        >
          {t("กลับ")}
        </Button>
        <Button
          type="button"
          disabled={busy || !canConfirm}
          onClick={onConfirm}
        >
          {busy ? t("กำลังบันทึก…") : t("ยืนยัน")}
        </Button>
      </div>
    </dialog>
  );
}
