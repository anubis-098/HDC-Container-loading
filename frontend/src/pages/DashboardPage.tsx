import { t, useLanguage, locale } from "../lib/i18n";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Download, RefreshCw, Search } from "lucide-react";
import { Button } from "../components/ui/button";
import { api, message, type Trip } from "../lib/api";
type Row = Trip & { shipment_count: number; photo_count: number };
type Summary = {
  trips: number;
  open: number;
  done: number;
  shipments: number;
  photos: number;
};
export function DashboardPage() {
  useLanguage();
  const [rows, setRows] = useState<Row[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    let active = true;
    setBusy(true);
    setError("");
    Promise.all([
      api<Row[]>(
        `/admin/trips?q=${encodeURIComponent(query)}&offset=${offset}`,
      ),
      api<Summary>("/admin/summary"),
    ])
      .then(([data, stats]) => {
        if (active) {
          setRows(data);
          setSummary(stats);
        }
      })
      .catch((error) => {
        if (active) setError(message(error));
      })
      .finally(() => {
        if (active) setBusy(false);
      });
    return () => {
      active = false;
    };
  }, [query, offset, reload]);
  function exportCsv() {
    const cell = (v: unknown) =>
      '"' +
      String(v ?? "")
        .replace(/^[=+@-]/, "'$&")
        .replaceAll('"', '""') +
      '"';
    const lines = [
      [
        "Truck ID",
        t("จังหวัดป้ายทะเบียน"),
        "Truck Type",
        t("ผู้บันทึก"),
        t("สถานะ"),
        "Shipment",
        "Photos",
        t("เวลาสร้าง"),
      ],
      ...rows.map((row) => [
        row.truck_id,
        row.truck_province,
        row.truck_type,
        row.worker_name,
        row.status,
        row.shipment_count,
        row.photo_count,
        row.created_at,
      ]),
    ];
    const url = URL.createObjectURL(
      new Blob(
        ["\ufeff" + lines.map((line) => line.map(cell).join(",")).join("\r\n")],
        { type: "text/csv;charset=utf-8" },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "container-loading-current-page.csv";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return (
    <section>
      <h1>Dashboard</h1>
      <p>{t("ภาพรวมการโหลดสินค้าและภาพรวมของแต่ละเที่ยวรถ")}</p>
      {summary && (
        <div className="stats-grid">
          {[
            [t("เที่ยวรถทั้งหมด"), summary.trips],
            [t("งานค้าง"), summary.open],
            [t("ปิดงานแล้ว"), summary.done],
            ["Shipment", summary.shipments],
            [t("ภาพทั้งหมด"), summary.photos],
          ].map(([label, value]) => (
            <div className="stat-card" key={label}>
              <span>{label}</span>
              <b>{value}</b>
            </div>
          ))}
        </div>
      )}
      <div className="panel">
        <form
          className="table-tools"
          onSubmit={(event) => {
            event.preventDefault();
            setQuery(search);
            setOffset(0);
            setReload((value) => value + 1);
          }}
        >
          <input
            aria-label={t("ค้นหาเที่ยวรถ")}
            maxLength={100}
            placeholder="Truck ID / Shipment / Store"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <Button disabled={busy}>
            <Search size={16} />
            {t("ค้นหา")}
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={() => setReload((value) => value + 1)}
          >
            <RefreshCw size={16} />
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={!rows.length || busy}
            onClick={exportCsv}
          >
            <Download size={16} />
            {t("CSV หน้านี้")}
          </Button>
        </form>
        {error && (
          <p className="error-box" role="alert">
            {t(error)}
          </p>
        )}
        {busy ? (
          <p role="status">{t("กำลังโหลด…")}</p>
        ) : (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{t("ทะเบียนรถ")}</th>
                  <th>{t("ผู้บันทึก")}</th>
                  <th>Shipment</th>
                  <th>Photos</th>
                  <th>{t("สถานะ")}</th>
                  <th>{t("วันที่")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <Link className="text-link" to={`/admin/trips/${row.id}`}>
                        {row.truck_id} {row.truck_province}
                      </Link>
                      <small>{row.truck_type}</small>
                    </td>
                    <td>{row.worker_name}</td>
                    <td>{row.shipment_count}</td>
                    <td>{row.photo_count}</td>
                    <td>
                      <span
                        className={`status-badge ${row.status === "DONE" ? "done" : ""}`}
                      >
                        {row.status === "DONE" ? t("ปิดงานแล้ว") : t("งานค้าง")}
                      </span>
                    </td>
                    <td>{new Date(row.created_at).toLocaleString(locale())}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rows.length && (
              <p className="empty-state">{t("ไม่พบเที่ยวรถตามเงื่อนไข")}</p>
            )}
          </div>
        )}
        <div className="pagination">
          <Button
            variant="outline"
            disabled={busy || offset === 0}
            onClick={() => setOffset((value) => Math.max(0, value - 50))}
          >
            {t("ก่อนหน้า")}
          </Button>
          <span>
            {t("หน้า")}
            {offset / 50 + 1}
          </span>
          <Button
            variant="outline"
            disabled={busy || rows.length < 50}
            onClick={() => setOffset((value) => value + 50)}
          >
            {t("ถัดไป")}
          </Button>
        </div>
      </div>
    </section>
  );
}
