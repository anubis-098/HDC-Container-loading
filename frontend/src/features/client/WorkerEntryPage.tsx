import { t, useLanguage, locale } from "../../lib/i18n";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  LockKeyhole,
  PackageCheck,
  Truck,
  Camera,
  UserRound,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import {
  api,
  message,
  remember,
  saved,
  uid,
  type Identity,
} from "../../lib/api";
export function WorkerEntryPage() {
  useLanguage();
  const navigate = useNavigate();
  const [name, setName] = useState(() => saved("worker-name"));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [existing, setExisting] = useState<Identity | null>(null);
  useEffect(() => {
    api<Identity>("/worker/me")
      .then(setExisting)
      .catch(() => {});
  }, []);
  async function start() {
    if (name.trim().length < 2) {
      setError(t("กรุณากรอกชื่อ–นามสกุล"));
      return;
    }
    setBusy(true);
    setError("");
    try {
      const identity = await api<Identity>("/worker/session", {
        method: "POST",
        body: JSON.stringify({ name: name.trim() }),
      });
      remember("worker-name", name.trim());
      // Starting a new trip must not restore the previous trip or reuse its ID.
      // Existing jobs and their pending photo queues remain available to resume.
      remember("active-trip", "");
      remember("truck-draft", "");
      remember("province-draft", "");
      remember("truck-type-draft", "");
      remember("trip-request-v2:" + identity.id, uid());
      navigate("/client/loading");
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="entry-intro">
        <div className="entry-eyebrow">
          <PackageCheck size={16} /> LOADING OPERATIONS
        </div>
        <h1>{t("พร้อมเริ่มโหลดสินค้า")}</h1>
        <p>{t("บันทึกเที่ยวรถและภาพสินค้าในเที่ยวรถ ก่อนส่งถึงปลายทาง")}</p>
        <ol className="entry-workflow" aria-label={t("ขั้นตอนการทำงาน")}>
          <li>
            <Truck size={19} />
            <span>{t("ข้อมูลรถ")}</span>
          </li>
          <li>
            <Camera size={19} />
            <span>{t("ภาพต่อ Trip")}</span>
          </li>
          <li>
            <PackageCheck size={19} />
            <span>{t("ตรวจสอบงาน")}</span>
          </li>
        </ol>
      </div>
      <form
        className="worker-login client-form"
        onSubmit={(event) => {
          event.preventDefault();
          void start();
        }}
      >
        <div className="entry-form-title">
          <UserRound size={19} />
          <h2>{t("ผู้ปฏิบัติงาน")}</h2>
        </div>
        <label>
          {t("ชื่อ–นามสกุล")}
          <input
            required
            minLength={2}
            maxLength={160}
            value={name}
            autoComplete="name"
            enterKeyHint="go"
            onChange={(event) => setName(event.target.value)}
            placeholder={t("กรอกชื่อและนามสกุลของคุณ")}
            disabled={busy}
          />
        </label>
        {error && (
          <div className="error-box" role="alert">
            {t(error)}
          </div>
        )}
        <Button className="start-trip-guide" disabled={busy} type="submit">
          {busy ? t("กำลังเข้าสู่ระบบ…") : t("เริ่มบันทึกเที่ยวรถ")}
          <ArrowRight size={20} />
        </Button>
        <p className="client-hint">
          {t("ระบุชื่อเพื่อใช้เป็นข้อมูลผู้บันทึกในเที่ยวรถนี้")}
        </p>
        {existing && (
          <Link className="resume-link" to="/client/loading">
            {t("ทำงานต่อในชื่อ")}
            {existing.name} →
          </Link>
        )}
      </form>
      <Link className="admin-entry" to="/admin/login">
        <LockKeyhole size={24} />
        <span>
          <b>{t("เข้าสู่ระบบผู้ดูแล")}</b>
          <small>{t("Dashboard และจัดการข้อมูล")}</small>
        </span>
        <ArrowRight size={20} />
      </Link>
      <footer className="client-credit">
        CJ Logistics · Container Loading
      </footer>
    </>
  );
}
