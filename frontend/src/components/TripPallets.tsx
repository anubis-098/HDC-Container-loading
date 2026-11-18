import { StorePicker } from "./StorePicker";
import { useEffect, useRef, useState } from "react";
import { Plus, Camera } from "lucide-react";
import {
  api,
  message,
  uid,
  type Trip,
  type Store,
  type Pallet,
} from "../lib/api";
import { type PendingPhoto } from "../lib/photoQueue";
import { PhotoTile } from "./PhotoTile";
import { Button } from "./ui/button";

export function TripPallets({
  trip,
  stores,
  disabled,
  canCapture,
  pending,
  onUpdated,
  onCapture,
  onDiscard,
  onEditingChange,
}: {
  trip: Trip;
  stores: Store[];
  disabled: boolean;
  canCapture: boolean;
  pending: PendingPhoto[];
  onUpdated: (trip: Trip) => void;
  onCapture: (files: File[], palletId: string) => void;
  onDiscard: (photo: PendingPhoto) => void;
  onEditingChange: (editing: boolean) => void;
}) {
  const [form, setForm] = useState(false),
    [editing, setEditing] = useState<Pallet | null>(null),
    [store, setStore] = useState(""),
    [orders, setOrders] = useState<string[]>([""]),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  const request = useRef(uid()),
    lock = useRef(false);
  const editor = useRef<HTMLFormElement>(null);
  const orderInputs = useRef<(HTMLInputElement | null)[]>([]);
  const nextFocus = useRef<number | null>(null);
  const done = trip.status !== "OPEN";
  useEffect(() => {
    if (form) {
      editor.current?.scrollIntoView({ behavior: "smooth", block: "center" });
      editor.current?.querySelector("select")?.focus({ preventScroll: true });
    }
  }, [form, editing]);
  useEffect(() => {
    if (nextFocus.current !== null) {
      orderInputs.current[nextFocus.current]?.focus();
      nextFocus.current = null;
    }
  }, [orders.length]);
  function addOrder() {
    if (orders.length >= 100) return;
    nextFocus.current = orders.length;
    setOrders((values) => [...values, ""]);
  }
  useEffect(() => {
    onEditingChange(form);
  }, [form, onEditingChange]);
  useEffect(() => () => onEditingChange(false), [onEditingChange]);
  useEffect(() => {
    const warn = (event: BeforeUnloadEvent) => {
      if (form) {
        event.preventDefault();
        event.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [form]);
  function open(pallet?: Pallet) {
    request.current = pallet?.id || uid();
    setEditing(pallet || null);
    setStore(pallet?.store_code || "");
    setOrders(pallet?.orders.length ? pallet.orders : [""]);
    setError("");
    setForm(true);
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (lock.current) return;
    lock.current = true;
    setSaving(true);
    setError("");
    try {
      const body = {
        id: request.current,
        store_code: store,
        orders: orders.map((v) => v.trim()).filter(Boolean),
      };
      if (!body.orders.length) throw new Error("กรุณากรอกเลข Order อย่างน้อย 1 เลข");
      if (new Set(body.orders).size !== body.orders.length)
        throw new Error("เลข Order ซ้ำใน Pallet นี้");
      const result = await api<Trip>(
        `/trips/${trip.id}/pallets${editing ? "/" + editing.id : ""}`,
        { method: editing ? "PUT" : "POST", body: JSON.stringify(body) },
      );
      onUpdated(result);
      setForm(false);
    } catch (e) {
      setError(message(e));
    } finally {
      lock.current = false;
      setSaving(false);
    }
  }
  return (
    <section className="pallet-section">
      <div className="panel pallet-heading">
        <h2>
          Pallet <span className="pallet-count">{trip.pallets.length}</span>
        </h2>
        {!done && !form && (
          <Button disabled={disabled} onClick={() => open()}>
            <Plus size={18} />
            เพิ่ม Pallet
          </Button>
        )}
      </div>
      {form && (
        <form
          ref={editor}
          className="panel client-form pallet-editor"
          onSubmit={(e) => void save(e)}
        >
          <h2>{editing ? `แก้ไข Pallet ${editing.number}` : "เพิ่ม Pallet"}</h2>
          <StorePicker stores={stores} value={store} onChange={setStore} disabled={disabled || saving}
            existing={editing ? {code: editing.store_code, name: editing.store_name} : undefined} />
          <div className="pallet-orders-label">
            เลข Order <small>บังคับอย่างน้อย 1 เลข · เพิ่มได้หลายเลข</small>
          </div>
          {orders.map((order, index) => (
            <div className="order-input-row" key={index}>
              <input
                ref={(element) => { orderInputs.current[index] = element; }}
                aria-label={`เลข Order ${index + 1}`}
                required={index === 0}
                className={index === 0 ? "required-entry" : undefined}
                maxLength={80}
                value={order}
                disabled={disabled || saving}
                placeholder="สแกนหรือกรอกเลข Order"
                onChange={(e) =>
                  setOrders((values) =>
                    values.map((v, i) => (i === index ? e.target.value : v)),
                  )
                }
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addOrder();
                  }
                }}
              />
              {orders.length > 1 && (
                <button
                  type="button"
                  className="order-remove"
                  aria-label={`ลบเลข Order ${index + 1}`}
                  disabled={disabled || saving}
                  onClick={() =>
                    setOrders((values) => values.filter((_, i) => i !== index))
                  }
                >
                  ×
                </button>
              )}
            </div>
          ))}
          <Button
            type="button"
            variant="outline"
            disabled={disabled || saving || orders.length >= 100}
            onClick={addOrder}
          >
            <Plus size={16} />
            เพิ่มเลข Order
          </Button>
          {error && (
            <p className="error-box" role="alert">
              {error}
            </p>
          )}
          <div className="pallet-form-actions">
            <Button
              type="button"
              variant="outline"
              disabled={saving}
              onClick={() => setForm(false)}
            >
              ยกเลิก
            </Button>
            <Button disabled={disabled || saving || !store}>
              {saving ? "กำลังบันทึก…" : "บันทึก Pallet"}
            </Button>
          </div>
        </form>
      )}
      {!trip.pallets.length && !form && (
        <div className="panel empty-state">
          ยังไม่มี Pallet · กด “เพิ่ม Pallet” เพื่อเลือก Store
        </div>
      )}
      {trip.pallets.map((pallet) => {
        const queued = pending.filter(
          (p) =>
            p.palletId === pallet.id &&
            !pallet.photos.some((photo) => photo.id === p.photoId),
        );
        return (
          <article className="panel pallet-card" key={pallet.id}>
            <div className="pallet-card-top">
              <div>
                <h3>Pallet {pallet.number}</h3>
                <p>
                  {pallet.store_code} · {pallet.store_name}
                </p>
              </div>
              {!done && (
                <Button
                  variant="outline"
                  disabled={disabled || saving}
                  onClick={() => open(pallet)}
                >
                  แก้ไข
                </Button>
              )}
            </div>
            <div className="order-tags">
              {pallet.orders.length ? (
                pallet.orders.map((order) => <span key={order}>{order}</span>)
              ) : (
                <small>{done ? "ไม่ระบุเลข Order" : "ยังไม่มีเลข Order · กดแก้ไขเพื่อระบุ"}</small>
              )}
            </div>
            <div className="pallet-photo-title">
              <b>ภาพ Pallet · {pallet.photos.length} ภาพ</b>
              {queued.length > 0 && <small>รอส่ง {queued.length}</small>}
            </div>
            {!done && (
              <div className="trip-capture-actions">
                <label className="camera-button">
                  <Camera size={20} />
                  ถ่ายภาพ
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    capture="environment"
                    disabled={disabled || !canCapture}
                    aria-label={`ถ่ายภาพ Pallet ${pallet.number}`}
                    onChange={(e) => {
                      const files = Array.from(e.target.files || []);
                      e.target.value = "";
                      if (files.length) onCapture(files, pallet.id);
                    }}
                  />
                </label>
                <label className="camera-button gallery-button">
                  <Plus size={18} />
                  เลือกภาพ
                  <input
                    type="file"
                    multiple
                    accept="image/jpeg,image/png,image/webp"
                    disabled={disabled || !canCapture}
                    aria-label={`เลือกภาพ Pallet ${pallet.number}`}
                    onChange={(e) => {
                      const files = Array.from(e.target.files || []);
                      e.target.value = "";
                      if (files.length) onCapture(files, pallet.id);
                    }}
                  />
                </label>
              </div>
            )}
            <div className="capture-grid">
              {pallet.photos.map((photo, i) => (
                <PhotoTile
                  key={photo.id}
                  label={`Pallet ${pallet.number} · ${i + 1}`}
                  photo={photo}
                  disabled
                  onCapture={() => {}}
                />
              ))}
              {queued.map((photo, i) => (
                <div key={photo.key}>
                  <PhotoTile
                    label={`รอส่ง ${i + 1}`}
                    pending={photo}
                    disabled
                    onCapture={() => {}}
                  />
                  <Button
                    variant="outline"
                    disabled={disabled}
                    onClick={() => onDiscard(photo)}
                  >
                    ลบภาพรอส่ง
                  </Button>
                </div>
              ))}
            </div>
          </article>
        );
      })}
    </section>
  );
}
