import { t, useLanguage, locale } from "../../lib/i18n";
import { SiteHeader } from "../../components/SiteHeader";
import { Outlet } from "react-router-dom";
import { ArrowUp } from "lucide-react";
export function ClientLayout() {
  useLanguage();
  return (
    <div className="client-surface">
      <div className="handheld" id="client-top" tabIndex={-1}>
        <SiteHeader />
        <Outlet />
      </div>
      <a className="back-to-top" href="#client-top" aria-label={t("ขึ้นบนสุด")}>
        <ArrowUp size={20} />
      </a>
    </div>
  );
}
