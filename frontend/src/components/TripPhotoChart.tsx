import { t, useLanguage } from "../lib/i18n";
import { MAX_TRIP_PHOTOS } from "../lib/api";

export function TripPhotoChart({
  sent,
  pending,
}: {
  sent: number;
  pending: number;
}) {
  useLanguage();
  const total = sent + pending;
  const remaining = Math.max(0, MAX_TRIP_PHOTOS - total);
  const sentPercent = Math.min(100, (sent / MAX_TRIP_PHOTOS) * 100);
  const pendingPercent = Math.min(
    100 - sentPercent,
    (pending / MAX_TRIP_PHOTOS) * 100,
  );
  return (
    <div className="trip-photo-chart">
      <div
        className="trip-photo-ring"
        role="img"
        aria-label={t(
          "ทั้งหมด {0} จาก {1} ภาพ ส่งสำเร็จ {2} ภาพ รอส่ง {3} ภาพ เหลือ {4} ภาพ",
          total,
          MAX_TRIP_PHOTOS,
          sent,
          pending,
          remaining,
        )}
      >
        <svg viewBox="0 0 120 120" aria-hidden="true">
          <circle className="photo-ring-track" cx="60" cy="60" r="50" />
          <circle
            className="photo-ring-sent"
            cx="60"
            cy="60"
            r="50"
            pathLength="100"
            strokeDasharray={`${sentPercent} 100`}
          />
          <circle
            className="photo-ring-pending"
            cx="60"
            cy="60"
            r="50"
            pathLength="100"
            strokeDasharray={`${pendingPercent} 100`}
            strokeDashoffset={-sentPercent}
          />
        </svg>
        <div className="photo-ring-label" aria-hidden="true">
          <strong>{total}</strong>
          <span>/ {MAX_TRIP_PHOTOS}</span>
        </div>
      </div>
    </div>
  );
}
