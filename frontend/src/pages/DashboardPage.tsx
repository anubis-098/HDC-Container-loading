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
  const [selected, setSelected] = useState<string[]>([]);
  const [actionBusy, setActionBusy] = useState(false);
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
          setSelected([]);
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
      ...rows.filter(row => !selected.length || selected.includes(row.id)).map((row) => [
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
      <div className="table-tools">
        <Button disabled={busy || !selected.length || actionBusy} onClick={async () => {
          setActionBusy(true); setError('');
          try {
            const response = await fetch('/api/admin/trips/photos.zip', {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json'}, body:JSON.stringify(selected)});
            if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail || 'Download failed'); }
            const url = URL.createObjectURL(await response.blob());
            const link = document.createElement('a'); link.href=url; link.download='container-loading-photos.zip'; link.click();
            setTimeout(() => URL.revokeObjectURL(url),1000);
          } catch(error) { setError(message(error)); }
          finally { setActionBusy(false); }
        }}><Download size={16}/>ดาวน์โหลดรูปที่เลือก ({selected.length})</Button>
        <Button disabled={!selected.length || actionBusy} onClick={exportCsv}>{t("ดาวน์โหลดที่เลือก")} ({selected.length}) CSV</Button>
        <Button disabled={!selected.length || actionBusy} onClick={async () => {
          if (!window.confirm(t("ยืนยันลบรายการที่เลือกและภาพทั้งหมด?"))) return;
          setActionBusy(true);
          try { for (const id of selected) { await api(`/admin/trips/${id}`, {method:"DELETE"}); setSelected(values => values.filter(value => value !== id)); } }
          catch (error) { setError(message(error)); }
          finally { setActionBusy(false); setReload(value => value + 1); }
        }}>{t("ลบที่เลือก")}</Button>
      </div>
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
                <tr><th><input type="checkbox" aria-label={t("เลือกทั้งหมดในหน้านี้")} disabled={actionBusy || !rows.length} checked={rows.length > 0 && selected.length === rows.length} onChange={e => setSelected(e.target.checked ? rows.map(row => row.id) : [])} /></th>
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
                  <tr key={row.id}><td><input type="checkbox" aria-label={row.truck_id} disabled={actionBusy} checked={selected.includes(row.id)} onChange={e => setSelected(values => e.target.checked ? [...values,row.id] : values.filter(id => id !== row.id))} /></td>
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
