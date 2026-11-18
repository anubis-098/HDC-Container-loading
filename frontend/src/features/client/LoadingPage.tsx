import { useStoreRefresh } from "../../components/StorePicker";
import { t, useLanguage, locale } from "../../lib/i18n";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Plus,
  RefreshCw,
  Truck,
  Send,
  CheckCircle2,
  WifiOff,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { TripPallets } from "../../components/TripPallets";
import { PhotoTile } from "../../components/PhotoTile";
import { TripPhotoChart } from "../../components/TripPhotoChart";
import { CloseTripDialog } from "../../components/CloseTripDialog";
import { ProvinceField } from "../../components/ProvinceField";
import { PlateReader } from "../../components/PlateReader";
import {
  api,
  ApiError,
  message,
  remember,
  saved,
  truckTypes,
  MAX_TRIP_PHOTOS,
  uid,
  type Identity,
  type Trip,
  type Store,
} from "../../lib/api";
import {
  acknowledge,
  allPending,
  compress,
  enqueue,
  type PendingPhoto,
} from "../../lib/photoQueue";
export function LoadingPage() {
  useLanguage();
  const navigate = useNavigate();
  const [who, setWho] = useState<Identity | null>(null);
  const [stores, setStores] = useState<Store[]>([]);
  useStoreRefresh(setStores);
  const [provinces, setProvinces] = useState<{ name: string }[]>([]);
  const [province, setProvince] = useState(() => saved("province-draft"));
  const [jobs, setJobs] = useState<Trip[]>([]);
  const [trip, setTrip] = useState<Trip | null>(null);
  const [truck, setTruck] = useState(() => saved("truck-draft"));
  const [truckType, setTruckType] = useState(() =>
    truckTypes.some((type) => type === saved("truck-type-draft"))
      ? saved("truck-type-draft")
      : "",
  );
  const [queue, setQueue] = useState<PendingPhoto[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [ready, setReady] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const [confirmClose, setConfirmClose] = useState(false);
  const [palletEditing, setPalletEditing] = useState(false);
  const syncingRef = useRef(false);
  const mounted = useRef(true);
  const currentId = useRef("");
  const tripRequest = useRef(uid());
  const captureLock = useRef(false);
  const actionLock = useRef(false);
  const pending = queue.filter((item) => item.tripId === trip?.id);
  function showError(error: unknown) {
    setError(message(error));
    if (error instanceof ApiError && error.status === 401) navigate("/");
  }
  async function refresh(id: string) {
    const next = await api<Trip>(`/trips/${id}`);
    if (mounted.current && currentId.current === id) setTrip(next);
    return next;
  }
  async function sync(id: string) {
    if (syncingRef.current) return;
    syncingRef.current = true;
    setSyncing(true);
    setError("");
    try {
      const current = await refresh(id);
      if (current.status !== "OPEN") return;
      const items = (await allPending()).filter((item) => item.tripId === id);
      for (const item of items) {
        const body = new FormData();
        body.append("file", item.blob, "trip.jpg");
        const path = item.photoId
          ? `/trips/${id}/photos/${item.photoId}${item.palletId && !item.side ? "?pallet_id=" + item.palletId : ""}`
          : `/trips/${id}/pallets/${item.palletId}/photos/${item.side}`;
        await api(path, {
          method: "PUT",
          body,
        });
        await acknowledge(item);
        if (mounted.current) setQueue(await allPending());
      }
      await refresh(id);
    } catch (error) {
      if (mounted.current) showError(error);
    } finally {
      syncingRef.current = false;
      if (mounted.current) setSyncing(false);
    }
  }
  useEffect(() => {
    mounted.current = true;
    let active = true;
    async function load() {
      try {
        const identity = await api<Identity>("/worker/me");
        if (!active) return;
        setWho(identity);
        tripRequest.current = saved("trip-request-v2:" + identity.id) || uid();
        const [storeList, jobList, provinceList] = await Promise.all([
          api<Store[]>("/stores"),
          api<Trip[]>("/trips"),
          api<{ name: string }[]>("/provinces"),
        ]);
        if (!active) return;
        setStores(storeList);
        setProvinces(provinceList);
        setJobs(jobList);
        const selected = saved("active-trip");
        const owned = jobList.find((item) => item.id === selected);
        if (owned) {
          currentId.current = owned.id;
          await refresh(owned.id);
          if (owned.status === "OPEN") void sync(owned.id);
        }
        setQueue(await allPending());
      } catch (error) {
        if (active) {
          setLoadFailed(true);
          showError(error);
        }
      } finally {
        if (active) setReady(true);
      }
    }
    void load();
    const onOnline = () => {
      setOnline(true);
      if (currentId.current) void sync(currentId.current);
    };
    const onOffline = () => setOnline(false);
    window.addEventListener("online", onOnline);
    window.addEventListener("offline", onOffline);
    return () => {
      active = false;
      mounted.current = false;
      window.removeEventListener("online", onOnline);
      window.removeEventListener("offline", onOffline);
    };
  }, []);
  async function action(run: () => Promise<void>) {
    if (busy || syncing || actionLock.current || syncingRef.current) return;
    actionLock.current = true;
    setBusy(true);
    setError("");
    try {
      await run();
    } catch (error) {
      showError(error);
    } finally {
      actionLock.current = false;
      setBusy(false);
    }
  }
  async function startTrip() {
    if (
      province.trim() &&
      !provinces.some((item) => item.name === province.trim())
    )
      throw new Error(t("กรุณาเลือกจังหวัดป้ายทะเบียนจากรายการ"));
    remember("trip-request-v2:" + who?.id, tripRequest.current);
    const created = await api<Trip>("/trips", {
      method: "POST",
      body: JSON.stringify({
        id: tripRequest.current,
        truck_id: truck.trim(),
        truck_province: province.trim() || null,
        truck_type: truckType.trim(),
      }),
    });
    currentId.current = created.id;
    setTrip(created);
    remember("active-trip", created.id);
    setJobs(await api<Trip[]>("/trips"));
  }
  async function takePhotos(files: File[], palletId?: string) {
    if (!trip || trip.status !== "OPEN" || busy || syncing || captureLock.current) return;
    captureLock.current = true;
    setBusy(true);
    setError("");
    try {
      const queued = (await allPending()).filter(
        (item) => item.tripId === trip.id,
      );
      const alreadyQueued = queued.filter(
        (item) =>
          !item.photoId ||
          !trip.photos.some((photo) => photo.id === item.photoId),
      ).length;
      if (trip.photos.length + alreadyQueued + files.length > MAX_TRIP_PHOTOS)
        throw new Error(t("รวมภาพที่รอส่งแล้ว ต้องไม่เกิน 120 ภาพต่อ Trip"));
      for (const file of files) {
        await enqueue(trip.id, await compress(file), palletId);
        if (mounted.current) setQueue(await allPending());
      }
      setQueue(await allPending());
      void sync(trip.id);
    } catch (error) {
      showError(error);
      setQueue(await allPending().catch(() => []));
    } finally {
      captureLock.current = false;
      setBusy(false);
    }
  }
  function newTrip() {
    currentId.current = "";
    setTrip(null);
    remember("active-trip", "");
    tripRequest.current = uid();
    remember("trip-request-v2:" + who?.id, tripRequest.current);
    setTruck("");
    setProvince("");
    remember("province-draft", "");
    setTruckType("");
    remember("truck-draft", "");
    remember("truck-type-draft", "");
    setConfirmClose(false);
    setError("");
  }
  const photoCount = trip?.photos.length || 0;
  const queuedOnly = pending.filter(
    (item) =>
      !item.photoId || !trip?.photos.some((photo) => photo.id === item.photoId),
  );
  const totalPhotos = photoCount + queuedOnly.length;
  const complete =
    !!trip &&
    !palletEditing &&
    (trip.structure_version === 1
      ? trip.shipments.length === 1
      : trip.pallets.length > 0 && trip.pallets.every(pallet=>pallet.orders.length>0)) &&
    photoCount >= 1 &&
    pending.length === 0;
  const cancelled = trip?.status === "CANCELLED";
  const done = !!trip && trip.status !== "OPEN";
  const disabled = busy || syncing;
  if (loadFailed)
    return (
      <div className="panel client-form">
        <h2>{t("ยังโหลดข้อมูลเริ่มต้นไม่ครบ")}</h2>
        <p role="alert" className="error-box">
          {t(error)}
        </p>
        <p>{t("ตรวจการเชื่อมต่อแล้วลองใหม่ ภาพรอส่งยังเก็บอยู่ในเครื่อง")}</p>
        <Button onClick={() => window.location.reload()}>
          {t("ลองโหลดใหม่")}
        </Button>
      </div>
    );
  if (!ready)
    return (
      <div className="worker-login" role="status">
        {t("กำลังโหลดงาน…")}
      </div>
    );
  return (
    <>
      <div className="work-context">
        <div className="work-context-row">
        <div className="worker-heading">
          <div className="worker-avatar">{who?.name.slice(0, 1)}</div>
          <div className="worker-name">
            <b>{who?.name}</b>
            <small>{t("ผู้ปฏิบัติงาน · โหลดสินค้า")}</small>
          </div>
        </div>
        {trip && (
            <div className="trip-summary work-trip-tab">
              <div>
                <h2>
                  <Truck size={19} />
                  <span className="trip-registration">{trip.truck_id}</span>
                  {trip.truck_province && <small>{trip.truck_province}</small>}
                </h2>
              </div>
              <div className="trip-context-meta">
                <span>{t(trip.truck_type)}</span>
                <span>{trip.pallets.length} Pallet</span>
              <span className={`status-badge ${done ? "done" : ""}`}>
                {cancelled ? t("ยกเลิกแล้ว") : done ? t("ปิดงานแล้ว") : t("กำลังโหลดสินค้า")}
              </span>
              </div>
            </div>
        )}
        </div>
        <div className="work-steps" aria-label={t("ความคืบหน้าของเที่ยวรถ")}>
          <span
            className={!trip ? "current" : "complete"}
            aria-current={!trip ? "step" : undefined}
          >
            <b>1</b>
            {t("ข้อมูลรถ")}
          </span>
          <span
            className={trip && !done ? "current" : done ? "complete" : ""}
            aria-current={trip && !done ? "step" : undefined}
          >
            <b>2</b>
            {t("Pallet และภาพ")}
          </span>
          <span
            className={done ? "current" : ""}
            aria-current={done ? "step" : undefined}
          >
            <b>3</b>
            {t("ปิดเที่ยวรถ")}
          </span>
        </div>
      </div>
      <div className="work-body">
        {!online && (
          <div className="notice">
            <WifiOff size={18} />
            {t("ออฟไลน์ · ภาพที่ถ่ายจะเก็บรอส่งในเครื่อง")}
          </div>
        )}
        {error && (
          <div className="error-box" role="alert">
            {t(error)}
          </div>
        )}
        {jobs.some(
          (item) => item.status === "OPEN" && item.id !== trip?.id,
        ) && (
          <details className="panel pending-jobs">
            <summary>
              {t("งานค้างของคุณ (")}
              {
                jobs.filter(
                  (item) => item.status === "OPEN" && item.id !== trip?.id,
                ).length
              }
              )
            </summary>
            {jobs
              .filter((item) => item.status === "OPEN" && item.id !== trip?.id)
              .map((item) => (
                <button
                  disabled={disabled}
                  key={item.id}
                  onClick={() =>
                    void action(async () => {
                      currentId.current = item.id;
                      remember("active-trip", item.id);
                      await refresh(item.id);
                      void sync(item.id);
                    })
                  }
                >
                  <Truck size={17} />
                  <span>
                    {item.truck_id}
                    <small>
                      {new Date(item.created_at).toLocaleString(locale())}
                    </small>
                  </span>
                  <span>{t("ทำต่อ →")}</span>
                </button>
              ))}
          </details>
        )}
        {!trip ? (
          <form
            className="panel client-form"
            onSubmit={(event) => {
              event.preventDefault();
              void action(startTrip);
            }}
          >
            <h2 className="section-heading">
              <span>1</span>
              {t("ข้อมูลรถ")}
            </h2>
            <p className="client-hint">
              {t("กรอกข้อมูลรถ แล้วเพิ่ม Pallet ในขั้นตอนถัดไป · จังหวัดไม่บังคับ")}
            </p>
            <div className="registration-row">
              <div className="registration-number-field">
                <label
                  className="plate-field-label"
                  htmlFor="truck-registration"
                >
                  {t("ป้ายทะเบียนรถ")}
                </label>
                <input
                  id="truck-registration"
                  className="required-entry"
                  enterKeyHint="next"
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.nativeEvent.isComposing
                    ) {
                      event.preventDefault();
                      document.getElementById("truck-province")?.focus();
                    }
                  }}
                  required
                  maxLength={40}
                  value={truck}
                  disabled={disabled}
                  onChange={(event) => {
                    setTruck(event.target.value);
                    remember("truck-draft", event.target.value);
                  }}
                  placeholder={t("เช่น 63-3512")}
                />
              </div>
              <ProvinceField
                value={province}
                provinces={provinces}
                disabled={disabled}
                onChange={(value) => {
                  setProvince(value);
                  remember("province-draft", value);
                }}
              />
            </div>
            <PlateReader
              disabled={disabled || !online}
              onSelect={(value) => {
                setTruck(value);
                remember("truck-draft", value);
              }}
            />
            <label>
              {t("ชนิดรถ")}
              <select
                required
                value={truckType}
                disabled={disabled}
                onChange={(event) => {
                  setTruckType(event.target.value);
                  remember("truck-type-draft", event.target.value);
                }}
              >
                <option value="">{t("เลือกชนิดรถ")}</option>
                {truckTypes.map((type) => (
                  <option key={type} value={type}>
                    {t(type)}
                  </option>
                ))}
              </select>
            </label>
            <Button disabled={disabled || !online}>
              {busy ? t("กำลังบันทึก…") : t("เริ่มเที่ยวรถ")}
            </Button>
          </form>
        ) : (
          <>
            {trip.shipments.map((shipment) => (
              <div className="panel shipment-panel" key={shipment.id}>
                <h2>{shipment.number}</h2>
                <p>
                  {shipment.store_code} · {shipment.store_name}
                </p>
              </div>
            ))}
            <TripPallets
              key={trip.id}
              onEditingChange={setPalletEditing}
              trip={trip}
              stores={stores}
              disabled={disabled}
              canCapture={totalPhotos < MAX_TRIP_PHOTOS}
              pending={pending}
              onUpdated={setTrip}
              onCapture={(files, palletId) => void takePhotos(files, palletId)}
              onDiscard={(item) => {
                if (window.confirm("ลบภาพนี้ออกจากคิวรอส่งในเครื่อง?"))
                  void action(async () => {
                    await acknowledge(item);
                    setQueue(await allPending());
                  });
              }}
            />
            {(trip.photos.some((photo) => !photo.pallet_id) || queuedOnly.some((item) => !item.palletId)) && (
            <div className="panel">
              <h2 className="section-heading">
                <span>2</span>
                {t("ภาพรวม Trip")}
              </h2>
              <div className="capture-grid">
                {trip.photos
                  .filter((photo) => !photo.pallet_id)
                  .map((photo, index) => (
                    <PhotoTile
                      key={photo.id}
                      label={t("ภาพที่ {0}", index + 1)}
                      photo={photo}
                      disabled
                      onCapture={() => {}}
                    />
                  ))}
                {queuedOnly
                  .filter((item) => !item.palletId)
                  .map((item, index) => (
                    <div key={item.key}>
                      <PhotoTile
                        label={t("รอส่ง ") + (index + 1)}
                        pending={item}
                        disabled
                        onCapture={() => {}}
                      />
                      <Button
                        type="button"
                        variant="outline"
                        className="full-width"
                        disabled={disabled}
                        onClick={() => {
                          if (window.confirm(t("ลบภาพนี้ออกจากคิวรอส่งในเครื่อง?")))
                            void action(async () => {
                              await acknowledge(item);
                              setQueue(await allPending());
                            });
                        }}
                      >
                        {t("ลบภาพรอส่ง")}
                      </Button>
                    </div>
                  ))}
              </div>
              {totalPhotos >= MAX_TRIP_PHOTOS && (
                <p className="notice">
                  {t("ครบ 120 ภาพแล้ว กรุณาส่งภาพที่ค้างและปิดเที่ยวรถ")}
                </p>
              )}
            </div>
            )}
            <div className="panel upload-summary">
              <h2 className="section-heading">
                <span>3</span>
                {cancelled ? t("ยกเลิกแล้ว") : done ? t("บันทึกสำเร็จ") : t("ตรวจสอบและส่งข้อมูล")}
              </h2>
              {pending.length > 0 && (
                <p>
                  {pending.length}
                  {t("ภาพรอส่ง · อย่าล้างข้อมูลเว็บไซต์จนกว่าจะส่งครบ")}
                </p>
              )}
              {!done && (
                <Button
                  variant="outline"
                  disabled={disabled || !online}
                  onClick={() => void sync(trip.id)}
                >
                  <RefreshCw size={17} />
                  {syncing ? t("กำลังส่งภาพ…") : t("ตรวจสอบ / ส่งภาพที่ค้างใหม่")}
                </Button>
              )}
              {done && !cancelled && (
                <p className="success-text">
                  <CheckCircle2 size={18} />{" "}
                  {t("ข้อมูลและภาพถูกบันทึกบนเซิร์ฟเวอร์แล้ว")}
                </p>
              )}
            </div>
            {confirmClose && !done && (
              <CloseTripDialog
                truckId={[trip.truck_id, trip.truck_province]
                  .filter(Boolean)
                  .join(" ")}
                photoCount={photoCount}
                busy={disabled}
                canConfirm={complete && online}
                error={t(error)}
                onBack={() => setConfirmClose(false)}
                onConfirm={() =>
                  void action(async () => {
                    const result = await api<Trip>(
                      `/trips/${trip.id}/complete`,
                      { method: "POST" },
                    );
                    setTrip(result);
                    setConfirmClose(false);
                    setJobs(await api<Trip[]>("/trips"));
                  })
                }
              />
            )}
            <div className="work-footer">
              <div className="work-footer-actions">
              <TripPhotoChart sent={photoCount} pending={queuedOnly.length} />
              {done ? (
                <Button className="full-width" onClick={newTrip}>
                  <Plus size={18} />
                  {t("เริ่ม Trip ถัดไป")}
                </Button>
              ) : (
                <Button
                  className="full-width"
                  disabled={!complete || disabled || !online}
                  onClick={() => setConfirmClose(true)}
                >
                  <Send size={18} />
                  {syncing ? t("กำลังส่งภาพ…") : t("ตรวจสอบและปิดเที่ยวรถ")}
                </Button>
              )}
              </div>
              {!complete && !done && (
                <small>
                  {t("กรอก Order ให้ทุก Pallet และส่งภาพที่ค้างให้ครบก่อนปิดเที่ยวรถ")}
                </small>
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}
