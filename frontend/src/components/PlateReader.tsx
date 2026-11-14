import { useState } from "react";
import { Camera, LoaderCircle } from "lucide-react";
import { api, message } from "../lib/api";
import { compress } from "../lib/photoQueue";
import { PlateCamera } from "./PlateCamera";
import { Button } from "./ui/button";
export function PlateReader({
  disabled,
  onSelect,
}: {
  disabled: boolean;
  onSelect: (value: string) => void;
}) {
  const [cameraOpen, setCameraOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function read(file: File) {
    setBusy(true);
    setError("");

    try {
      const body = new FormData();
      body.append("file", await compress(file), "plate.jpg");
      const result = await api<{ candidates: string[]; text: string }>(
        "/ocr/plate",
        { method: "POST", body },
      );
      const plate = result.candidates[0]?.trim();
      if (plate) onSelect(plate);
      else
        setError(
          "อ่านทะเบียนไม่สำเร็จ กรุณาถ่ายใหม่หรือพิมพ์ทะเบียนในช่องด้านบน",
        );
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="plate-reader">
      <Button
        type="button"
        variant="outline"
        className="plate-scan-trigger camera-action-button"
        disabled={disabled || busy}
        title="ถ่ายป้ายทะเบียนเพื่ออ่านตัวอักษร"
        aria-label="ถ่ายป้ายทะเบียนเพื่ออ่านตัวอักษร"
        onClick={() => {
          setError("");
          setCameraOpen(true);
        }}
      >
        {busy ? (
          <LoaderCircle size={20} className="animate-spin" />
        ) : (
          <Camera size={20} />
        )}
        <span>{busy ? "กำลังอ่านทะเบียน…" : "สแกนป้ายทะเบียน"}</span>
      </Button>
      {cameraOpen && (
        <PlateCamera
          onClose={() => setCameraOpen(false)}
          onCapture={(file) => {
            setCameraOpen(false);
            void read(file);
          }}
        />
      )}
      {busy && <p role="status">กำลังอ่านภาพ กรุณารอสักครู่</p>}
      {error && (
        <p role="alert" className="error-box">
          {error}
        </p>
      )}
    </div>
  );
}
