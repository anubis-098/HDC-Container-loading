import { t, useLanguage, locale } from "../lib/i18n";
import { useEffect, useRef, useState } from "react";
import {
  X,
  ZoomIn,
  ZoomOut,
  Maximize,
  ChevronLeft,
  ChevronRight,
  Download,
} from "lucide-react";
import { Button } from "./ui/button";
import type { Photo } from "../lib/api";
export const photoUrl = (photo: Photo) =>
  photo.archived_at
    ? `/api/admin/archived-photos/${photo.id}`
    : `/api/photos/${photo.id}`;
export function PhotoViewer({
  photos,
  initialIndex,
  onClose,
  onDownload,
  downloading,
  downloadError,
}: {
  photos: Photo[];
  initialIndex: number;
  onClose: () => void;
  onDownload: (photo: Photo, index: number) => void;
  downloading: boolean;
  downloadError: string;
}) {
  useLanguage();
  const dialog = useRef<HTMLDialogElement>(null);
  const viewport = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(initialIndex);
  const [zoom, setZoom] = useState(1);
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const photo = photos[index];
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    element.showModal();
    return () => {
      element.close();
      document.body.style.overflow = overflow;
    };
  }, []);
  useEffect(() => {
    setZoom(1);
    setFailed(false);
    setLoaded(false);
    viewport.current?.scrollTo(0, 0);
  }, [index]);
  function fit() {
    setZoom(1);
    viewport.current?.scrollTo(0, 0);
  }
  return (
    <dialog
      ref={dialog}
      className="photo-viewer"
      aria-labelledby="photo-viewer-title"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === dialog.current) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft") {
          event.preventDefault();
          setIndex((value) => Math.max(0, value - 1));
        }
        if (event.key === "ArrowRight") {
          event.preventDefault();
          setIndex((value) => Math.min(photos.length - 1, value + 1));
        }
      }}
    >
      <div className="photo-viewer-content">
        <div className="viewer-toolbar">
          <h2 id="photo-viewer-title">
            {t("ภาพที่")}
            {index + 1} / {photos.length}
            {photo.archived_at ? " · Archive" : ""}
          </h2>
          <Button
            variant="outline"
            autoFocus
            aria-label={t("ปิดภาพ")}
            title={t("ปิด (Esc)")}
            onClick={onClose}
          >
            <X size={20} />
          </Button>
        </div>
        <div className="viewer-tools">
          {downloadError && (
            <p role="alert" className="error-box viewer-error">
              {t(downloadError)}
            </p>
          )}
          <Button
            variant="outline"
            disabled={zoom <= 1 || failed || !loaded}
            aria-label={t("ซูมออก")}
            onClick={() => setZoom((value) => Math.max(1, value - 0.25))}
          >
            <ZoomOut size={19} />
          </Button>
          <span>{Math.round(zoom * 100)}%</span>
          <Button
            variant="outline"
            disabled={zoom >= 4 || failed || !loaded}
            aria-label={t("ซูมเข้า")}
            onClick={() => setZoom((value) => Math.min(4, value + 0.25))}
          >
            <ZoomIn size={19} />
          </Button>
          <Button
            variant="outline"
            aria-label={t("ปรับภาพพอดีหน้าจอ")}
            onClick={fit}
          >
            <Maximize size={18} />
            {t("พอดีจอ")}
          </Button>
          <Button
            disabled={downloading || failed}
            onClick={() => onDownload(photo, index)}
          >
            <Download size={18} />
            {downloading ? t("กำลังดาวน์โหลด…") : t("ดาวน์โหลด")}
          </Button>
        </div>
        <div
          className="viewer-viewport"
          ref={viewport}
          tabIndex={0}
          aria-label={t("ภาพขยาย เลื่อนเพื่อดูส่วนต่าง ๆ")}
        >
          {failed ? (
            <p role="alert">{t("โหลดภาพไม่สำเร็จ กรุณาปิดแล้วลองใหม่")}</p>
          ) : (
            <>
              <div
                className="viewer-canvas"
                style={{ width: `${zoom * 100}%`, height: `${zoom * 100}%` }}
              >
                <img
                  key={photo.id}
                  src={photoUrl(photo)}
                  alt={t("ภาพสินค้าใน Trip ลำดับ {0}", index + 1)}
                  onLoad={() => setLoaded(true)}
                  onError={() => setFailed(true)}
                  onDoubleClick={() => {
                    if (zoom === 1) setZoom(2);
                    else fit();
                  }}
                />
              </div>
              {!loaded && (
                <p className="viewer-loading" role="status">
                  {t("กำลังโหลดภาพ…")}
                </p>
              )}
            </>
          )}
        </div>
        <div className="viewer-navigation">
          <Button
            variant="outline"
            disabled={index === 0}
            onClick={() => setIndex((value) => value - 1)}
          >
            <ChevronLeft size={18} />
            {t("ก่อนหน้า")}
          </Button>
          <small>{t("ซูมแล้วเลื่อนภาพเพื่อดูรายละเอียด")}</small>
          <Button
            variant="outline"
            disabled={index === photos.length - 1}
            onClick={() => setIndex((value) => value + 1)}
          >
            {t("ถัดไป")}
            <ChevronRight size={18} />
          </Button>
        </div>
      </div>
    </dialog>
  );
}
