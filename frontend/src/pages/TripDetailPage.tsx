import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Download, FileText, ZoomIn } from "lucide-react";
import { api, message, type Trip, type Photo } from "../lib/api";
import { Button } from "../components/ui/button";
import { PhotoViewer, photoUrl } from "../components/PhotoViewer";
export function TripDetailPage() {
  const { tripId } = useParams();
  const [trip, setTrip] = useState<Trip | null>(null);
  const [error, setError] = useState("");
  const [downloadError, setDownloadError] = useState("");
  const [selected, setSelected] = useState<number | null>(null);
  const [downloading, setDownloading] = useState(false);
  useEffect(() => {
    let active = true;
    setTrip(null);
    setSelected(null);
    setError("");
    api<Trip>(`/trips/${tripId}`)
      .then((value) => {
        if (active) setTrip(value);
      })
      .catch((error) => {
        if (active) setError(message(error));
      });
    return () => {
      active = false;
    };
  }, [tripId]);
  async function download(path: string, filename: string) {
    if (downloading) return;
    setDownloading(true);
    setDownloadError("");
    try {
      const response = await fetch("/api" + path, {
        credentials: "same-origin",
      });
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.detail || "ดาวน์โหลดไม่สำเร็จ กรุณาลองใหม่");
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (error) {
      setDownloadError(message(error));
    } finally {
      setDownloading(false);
    }
  }
  function single(photo: Photo, index: number) {
    void download(
      `/admin/trips/${tripId}/photos/${photo.id}/download`,
      `trip-${tripId}-${String(index + 1).padStart(3, "0")}.jpg`,
    );
  }
  return (
    <section>
      <h1>รายละเอียดเที่ยวรถ</h1>
      {error && (
        <p className="error-box" role="alert">
          {error}
        </p>
      )}
      {!trip && !error && <p>กำลังโหลด…</p>}
      {trip && (
        <>
          <div className="panel">
            <h2>
              {trip.truck_id} {trip.truck_province} · {trip.truck_type}
            </h2>
            <p>
              ผู้บันทึก: {trip.worker_name} ·{" "}
              {trip.status === "DONE" ? "ปิดงานแล้ว" : "งานค้าง"}
            </p>
            <p>{new Date(trip.created_at).toLocaleString("th-TH")}</p>
          </div>
          <div className="panel">
            <h2>Shipment / Store</h2>
            {trip.shipments.map((item) => (
              <p key={item.id}>
                {item.number} → {item.store_code} · {item.store_name}
              </p>
            ))}
          </div>
          <div className="panel">
            <div className="evidence-actions">
              <h2>ภาพของ Trip · {trip.photos.length} ภาพ</h2>
              <Button
                variant="outline"
                disabled={!trip.photos.length || downloading}
                onClick={() =>
                  void download(
                    `/admin/trips/${tripId}/photos.zip`,
                    `trip-${tripId}.zip`,
                  )
                }
              >
                <Download size={17} /> ดาวน์โหลดทั้งหมด ZIP
              </Button>
              <Button
                disabled={!trip.photos.length || downloading}
                onClick={() =>
                  void download(
                    `/admin/trips/${tripId}/report.pdf`,
                    `trip-${tripId}.pdf`,
                  )
                }
              >
                <FileText size={17} /> รายงาน PDF
              </Button>
            </div>
            <p className="client-hint">
              คลิกภาพเพื่อซูม · PDF แนวนอน A4 จัด 6 ภาพต่อหน้า
            </p>
            {downloading && (
              <p role="status">กำลังเตรียมไฟล์ กรุณารอสักครู่…</p>
            )}
            {downloadError && (
              <p className="error-box" role="alert">
                {downloadError}
              </p>
            )}
            <div className="evidence-grid">
              {trip.photos.map((photo, index) => (
                <figure key={photo.id}>
                  <button
                    type="button"
                    className="evidence-thumbnail"
                    onClick={() => setSelected(index)}
                    aria-label={`ดูและซูมภาพที่ ${index + 1}`}
                  >
                    <img
                      src={photoUrl(photo)}
                      alt={`ภาพที่ ${index + 1}`}
                      loading="lazy"
                    />
                    <span>
                      <ZoomIn size={18} /> ดูภาพ
                    </span>
                  </button>
                  <figcaption>
                    ภาพที่ {index + 1}
                    {photo.archived_at ? " · Archive" : ""}
                  </figcaption>
                  <Button
                    variant="outline"
                    className="full-width"
                    disabled={downloading}
                    onClick={() => single(photo, index)}
                  >
                    <Download size={16} /> ดาวน์โหลด
                  </Button>
                </figure>
              ))}
            </div>
            {!trip.photos.length && <p>ยังไม่มีภาพ</p>}
          </div>
          {selected !== null && (
            <PhotoViewer
              photos={trip.photos}
              initialIndex={selected}
              onClose={() => setSelected(null)}
              onDownload={single}
              downloading={downloading}
              downloadError={downloadError}
            />
          )}
        </>
      )}
    </section>
  );
}
