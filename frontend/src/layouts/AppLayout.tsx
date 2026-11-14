import { SiteHeader } from "../components/SiteHeader";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUp,
  LayoutDashboard,
  Settings,
  Store,
  LogOut,
  Camera,
} from "lucide-react";
import { api, ApiError, message, type Identity } from "../lib/api";
export function AppLayout() {
  const navigate = useNavigate();
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api<Identity>("/admin/me")
      .then(setIdentity)
      .catch((error) => {
        if (error instanceof ApiError && error.status === 401)
          navigate("/admin/login", { replace: true });
        else setError(message(error));
      });
  }, [navigate]);
  if (!identity)
    return (
      <div className="panel">
        {error ? (
          <>
            <p role="alert" className="error-box">
              {error}
            </p>
            <button
              className="back-button"
              onClick={() => window.location.reload()}
            >
              ลองเชื่อมต่อใหม่
            </button>
          </>
        ) : (
          "กำลังตรวจสอบสิทธิ์…"
        )}
      </div>
    );
  return (
    <div className="app-shell" id="page-top" tabIndex={-1}>
      <aside>
        <img
          src="/branding/cj-logistics.png"
          alt="CJ Logistics"
          className="logo"
        />
        <h2>Container Loading</h2>
        <nav aria-label="เมนูหลัก">
          <NavLink to="/admin" end>
            <LayoutDashboard size={19} /> Dashboard
          </NavLink>
          <NavLink to="/admin/stores">
            <Store size={19} /> Store
          </NavLink>
          <NavLink to="/admin/settings">
            <Settings size={19} /> ตั้งค่า
          </NavLink>
          <NavLink to="/">
            <Camera size={19} /> หน้าพนักงาน
          </NavLink>
        </nav>
        <div className="admin-profile">
          <b>{identity.name}</b>
          <small>Administrator</small>
          <button
            className="back-button"
            onClick={async () => {
              try {
                await api("/admin/logout", { method: "POST" });
                navigate("/admin/login", { replace: true });
              } catch (error) {
                setError(message(error));
              }
            }}
          >
            <LogOut size={17} /> ออกจากระบบ
          </button>
        </div>
      </aside>
      <main>
        <SiteHeader />
        {error && (
          <p role="alert" className="error-box">
            {error}
          </p>
        )}
        <Outlet />
      </main>
      <a
        className="back-to-top"
        href="#page-top"
        aria-label="เลื่อนไปด้านบนสุด"
      >
        <ArrowUp size={20} />
        <span>ขึ้นบนสุด</span>
      </a>
    </div>
  );
}
