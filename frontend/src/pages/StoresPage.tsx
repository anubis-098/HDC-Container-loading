import { useEffect, useState } from "react";
import { api, message, type Store } from "../lib/api";
import { Button } from "../components/ui/button";
export function StoresPage() {
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
      <h1>จัดการ Store</h1>
      <p>เพิ่ม Store เพื่อให้พนักงานเลือกปลายทางได้</p>
      {error && (
        <div className="error-box" role="alert">
          {error}
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
          รหัส Store
          <input
            required
            pattern="[A-Za-z0-9_-]+"
            maxLength={40}
            value={code}
            disabled={busy || editingCode !== null}
            onChange={(event) => setCode(event.target.value)}
            placeholder="เช่น 1001"
          />
        </label>
        <label>
          ชื่อ Store
          <input
            required
            maxLength={160}
            value={name}
            disabled={busy}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <Button disabled={busy}>
          {editingCode ? "บันทึกการแก้ไข" : "เพิ่ม Store"}
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
            ยกเลิกแก้ไข
          </Button>
        )}
      </form>
      <div className="panel table-scroll">
        <table>
          <thead>
            <tr>
              <th>รหัส</th>
              <th>ชื่อ</th>
              <th>สถานะ</th>
              <th>จัดการ</th>
            </tr>
          </thead>
          <tbody>
            {stores.map((item) => (
              <tr key={item.code}>
                <td>{item.code}</td>
                <td>{item.name}</td>
                <td>{item.active ? "เปิดใช้งาน" : "ปิดใช้งาน"}</td>
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
                    แก้ไข
                  </Button>{" "}
                  <Button
                    variant="outline"
                    disabled={busy}
                    onClick={() => void save({ ...item, active: !item.active })}
                  >
                    {item.active ? "ปิดใช้งาน" : "เปิดใช้งาน"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!stores.length && <p className="empty-state">ยังไม่มี Store</p>}
      </div>
    </section>
  );
}
