import { MAX_TRIP_PHOTOS } from "../lib/api";

export function TripPhotoChart({
  sent,
  pending,
}: {
  sent: number;
  pending: number;
}) {
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
        aria-label={`ทั้งหมด ${total} จาก ${MAX_TRIP_PHOTOS} ภาพ ส่งสำเร็จ ${sent} ภาพ รอส่ง ${pending} ภาพ เหลือ ${remaining} ภาพ`}
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
          <span>/ {MAX_TRIP_PHOTOS} ภาพ</span>
        </div>
      </div>
      <div className="photo-chart-details">
        <h3>ภาพในเที่ยวรถ</h3>
        <dl>
          <div>
            <dt>
              <i className="photo-dot-sent" />
              ส่งสำเร็จ
            </dt>
            <dd>{sent}</dd>
          </div>
          <div>
            <dt>
              <i className="photo-dot-pending" />
              รอส่ง
            </dt>
            <dd>{pending}</dd>
          </div>
          <div>
            <dt>
              <i className="photo-dot-remaining" />
              เพิ่มได้อีก
            </dt>
            <dd>{remaining}</dd>
          </div>
        </dl>
        <small>อย่างน้อย 1 ภาพเพื่อปิดงาน</small>
      </div>
    </div>
  );
}
