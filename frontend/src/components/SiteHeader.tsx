import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Clock } from "./Clock";
export function SiteHeader() {
  const location = useLocation();
  const navigate = useNavigate();
  const home = location.pathname === "/";
  function back() {
    if (window.history.state?.idx > 0) navigate(-1);
    else
      navigate(
        location.pathname.startsWith("/admin/") &&
          location.pathname !== "/admin/login"
          ? "/admin"
          : "/",
      );
  }
  return (
    <header className="site-header">
      <button
        type="button"
        className="site-header-back"
        disabled={home}
        aria-label="ย้อนกลับไปหน้าก่อนหน้า"
        title="ย้อนกลับ"
        onClick={back}
      >
        <ArrowLeft size={20} />
      </button>
      <img
        className="site-header-logo"
        src="/branding/cj-logistics.png"
        alt="CJ Logistics"
        width={64}
        height={40}
      />
      <div className="site-header-title">
        <strong>Container Loading</strong>
        <small>ระบบบันทึกการโหลดสินค้า</small>
      </div>
      <Clock />
    </header>
  );
}
