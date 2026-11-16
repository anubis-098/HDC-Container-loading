import { t, useLanguage, locale } from "../lib/i18n";
import { useEffect, useState } from "react";
import { api, message, type Store } from "../lib/api";
import { Button } from "../components/ui/button";
export function StoresPage() {
  useLanguage();
  const [stores, setStores] = useState<Store[]>([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [active, setActive] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function load() {
    setStores(await api<Store[]>("/admin/stores"));
  }
  useEffect(() => {
    void load().catch((error) => setError(message(error)));
  }, []);
  async function save(item: Store) {
    setBusy(true);
    setError("");
    try {
      await api(`/admin/stores/${encodeURIComponent(item.code)}`, {
        method: "PUT",
        body: JSON.stringify(item),
      });
      await load();
      setCode("");
      setName("");
      setEditingCode(null);
      setActive(true);
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section>
      <h1>{t("จัดการ Store")}</h1>
      <p>{t("เพิ่ม Store เพื่อให้พนักงานเลือกปลายทางได้")}</p>
      {error && (
        <div className="error-box" role="alert">
          {t(error)}
        </div>
      )}
      <form
        className="panel table-tools"
        onSubmit={(event) => {
          event.preventDefault();
          void save({ code: code.trim(), name: name.trim(), active });
        }}
      >
        <label>
          {t("รหัส Store")}
          <input
            required
            pattern="[A-Za-z0-9_-]+"
            maxLength={40}
            value={code}
            disabled={busy || editingCode !== null}
            onChange={(event) => setCode(event.target.value)}
            placeholder={t("เช่น 1001")}
          />
        </label>
        <label>
          {t("ชื่อ Store")}
          <input
            required
            maxLength={160}
            value={name}
            disabled={busy}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <Button disabled={busy}>
          {editingCode ? t("บันทึกการแก้ไข") : t("เพิ่ม Store")}
        </Button>
        {editingCode && (
          <Button
            type="button"
            variant="outline"
            disabled={busy}
            onClick={() => {
              setEditingCode(null);
              setCode("");
              setName("");
              setActive(true);
            }}
          >
            {t("ยกเลิกแก้ไข")}
          </Button>
        )}
      </form>
      <div className="panel table-scroll">
        <table>
          <thead>
            <tr>
              <th>{t("รหัส")}</th>
              <th>{t("ชื่อ")}</th>
              <th>{t("สถานะ")}</th>
              <th>{t("จัดการ")}</th>
            </tr>
          </thead>
          <tbody>
            {stores.map((item) => (
              <tr key={item.code}>
                <td>{item.code}</td>
                <td>{item.name}</td>
                <td>{item.active ? t("เปิดใช้งาน") : t("ปิดใช้งาน")}</td>
                <td>
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() => {
                      setCode(item.code);
                      setName(item.name);
                      setEditingCode(item.code);
                      setActive(item.active);
                    }}
                  >
                    {t("แก้ไข")}
                  </Button>{" "}
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() => void save({ ...item, active: !item.active })}
                  >
                    {item.active ? t("ปิดใช้งาน") : t("เปิดใช้งาน")}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!stores.length && <p className="empty-state">{t("ยังไม่มี Store")}</p>}
      </div>
    </section>
  );
}
