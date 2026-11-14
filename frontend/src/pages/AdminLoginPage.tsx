import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { LockKeyhole } from "lucide-react";
import { Button } from "../components/ui/button";
import { api, message } from "../lib/api";
export function AdminLoginPage() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api("/admin/me")
      .then(() => navigate("/admin", { replace: true }))
      .catch(() => {});
  }, [navigate]);
  return (
    <div className="admin-login-page">
      <form
        className="panel client-form"
        onSubmit={async (event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          try {
            await api("/admin/login", {
              method: "POST",
              body: JSON.stringify({ username, password }),
            });
            setPassword("");
            navigate("/admin", { replace: true });
          } catch (error) {
            setError(message(error));
          } finally {
            setBusy(false);
          }
        }}
      >
        <h1>
          <LockKeyhole size={24} /> เข้าสู่ระบบ Admin
        </h1>
        <label>
          ชื่อผู้ใช้
          <input
            required
            autoComplete="username"
            autoCapitalize="none"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </label>
        <label>
          รหัสผ่าน
          <input
            required
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </label>
        {error && (
          <div className="error-box" role="alert">
            {error}
          </div>
        )}
        <Button disabled={busy}>
          {busy ? "กำลังตรวจสอบ…" : "เข้าสู่ระบบ"}
        </Button>
      </form>
      <p className="login-help">
        บัญชีผู้ดูแลสร้างโดยผู้ติดตั้งระบบ หากยังไม่มีบัญชี กรุณาติดต่อ IT
      </p>
    </div>
  );
}
