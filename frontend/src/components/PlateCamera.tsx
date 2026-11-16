import { t, useLanguage, locale } from "../lib/i18n";
import { useEffect, useRef, useState } from "react";
import { Camera, X } from "lucide-react";
import { Button } from "./ui/button";

export function PlateCamera({
  onClose,
  onCapture,
}: {
  onClose: () => void;
  onCapture: (file: File) => void;
}) {
  useLanguage();
  const dialog = useRef<HTMLDialogElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const frame = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const captureLock = useRef(false);
  const alive = useRef(false);
  useEffect(() => {
    alive.current = true;
    let cancelled = false;
    let stream: MediaStream | undefined;
    const element = dialog.current;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element?.showModal();
    async function start() {
      try {
        if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia)
          throw new Error(t("เปิดเว็บผ่าน HTTPS เพื่อใช้งานกล้อง"));
        stream = await navigator.mediaDevices.getUserMedia({
          audio: false,
          video: {
            facingMode: { ideal: "environment" },
            width: { ideal: 1920 },
            height: { ideal: 1080 },
          },
        });
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        if (video.current) {
          video.current.srcObject = stream;
          await video.current.play();
        }
      } catch (err) {
        if (!cancelled)
          setError(
            err instanceof DOMException
              ? err.name === "NotAllowedError"
                ? t("กรุณาอนุญาตการใช้กล้องใน Chrome แล้วลองใหม่")
                : t(
                    "เปิดกล้องไม่ได้ กรุณาตรวจสอบว่ามีกล้องพร้อมใช้งานและไม่ได้ถูกแอปอื่นใช้อยู่",
                  )
              : err instanceof Error
                ? err.message
                : t("เปิดกล้องไม่สำเร็จ"),
          );
      }
    }
    void start();
    return () => {
      cancelled = true;
      alive.current = false;
      stream?.getTracks().forEach((track) => track.stop());
      element?.close();
      document.body.style.overflow = overflow;
    };
  }, []);
  async function capture() {
    const source = video.current;
    const guide = frame.current;
    if (!source || !guide || !ready || captureLock.current) return;
    captureLock.current = true;
    setBusy(true);
    setError("");
    try {
      const bounds = source.getBoundingClientRect();
      const crop = guide.getBoundingClientRect();
      // Map the visible rectangle back to source pixels, including object-fit: cover cropping.
      const scale = Math.max(
        bounds.width / source.videoWidth,
        bounds.height / source.videoHeight,
      );
      const x =
        (crop.left -
          bounds.left +
          (source.videoWidth * scale - bounds.width) / 2) /
        scale;
      const y =
        (crop.top -
          bounds.top +
          (source.videoHeight * scale - bounds.height) / 2) /
        scale;
      const width = crop.width / scale,
        height = crop.height / scale;
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(width);
      canvas.height = Math.round(height);
      const context = canvas.getContext("2d");
      if (!context || !canvas.width || !canvas.height)
        throw new Error(t("กล้องยังไม่พร้อม กรุณาลองใหม่"));
      context.drawImage(
        source,
        x,
        y,
        width,
        height,
        0,
        0,
        canvas.width,
        canvas.height,
      );
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, "image/jpeg", 0.94),
      );
      if (!blob) throw new Error(t("บันทึกภาพไม่สำเร็จ กรุณาถ่ายใหม่"));
      if (alive.current)
        onCapture(new File([blob], "plate.jpg", { type: "image/jpeg" }));
    } catch (err) {
      if (alive.current)
        setError(err instanceof Error ? err.message : t("ถ่ายภาพไม่สำเร็จ"));
    } finally {
      captureLock.current = false;
      if (alive.current) setBusy(false);
    }
  }
  return (
    <dialog
      ref={dialog}
      className="plate-camera-dialog"
      aria-labelledby="plate-camera-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="plate-camera-heading">
        <h2 id="plate-camera-title">{t("สแกนป้ายทะเบียน")}</h2>
        <Button
          type="button"
          variant="outline"
          autoFocus
          aria-label={t("ปิดกล้อง")}
          onClick={onClose}
        >
          <X size={20} />
        </Button>
      </div>
      <p>{t("จัดป้ายทะเบียนให้อยู่ในกรอบ แล้วกดถ่ายภาพ")}</p>
      <div className="plate-camera-preview">
        <video
          ref={video}
          autoPlay
          muted
          playsInline
          onLoadedData={() => setReady(true)}
          onError={() => {
            setReady(false);
            setError(t("ภาพจากกล้องขัดข้อง กรุณาปิดแล้วเปิดใหม่"));
          }}
        />
        <div ref={frame} className="plate-camera-frame" aria-hidden="true" />
        {!ready && !error && (
          <span className="plate-camera-wait" role="status">
            {t("กำลังเปิดกล้อง…")}
          </span>
        )}
      </div>
      {error && (
        <p className="error-box" role="alert">
          {t(error)}
        </p>
      )}
      <div className="plate-camera-actions">
        <Button type="button" variant="outline" onClick={onClose}>
          {t("กลับ")}
        </Button>
        <Button
          type="button"
          className="camera-action-button"
          disabled={!ready || busy || !!error}
          onClick={() => void capture()}
        >
          <Camera size={20} />
          {busy ? t("กำลังถ่าย…") : t("ถ่ายภาพและอ่านทะเบียน")}
        </Button>
      </div>
    </dialog>
  );
}
