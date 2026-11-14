import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { DashboardPage } from "../pages/DashboardPage";
import { SettingsPage } from "../pages/SettingsPage";
import { StoresPage } from "../pages/StoresPage";
import { TripDetailPage } from "../pages/TripDetailPage";
import { AdminLoginPage } from "../pages/AdminLoginPage";
import { ClientLayout } from "../features/client/ClientLayout";
import { WorkerEntryPage } from "../features/client/WorkerEntryPage";
import { LoadingPage } from "../features/client/LoadingPage";
export const router = createBrowserRouter([
  {
    element: <ClientLayout />,
    children: [
      { index: true, element: <WorkerEntryPage /> },
      { path: "client/loading", element: <LoadingPage /> },
      { path: "client/*", element: <Navigate to="/client/loading" replace /> },
      { path: "admin/login", element: <AdminLoginPage /> },
    ],
  },
  {
    element: <AppLayout />,
    children: [
      { path: "admin", element: <DashboardPage /> },
      { path: "admin/stores", element: <StoresPage /> },
      { path: "admin/trips/:tripId", element: <TripDetailPage /> },
      { path: "admin/settings", element: <SettingsPage /> },
    ],
  },
  { path: "trips/*", element: <Navigate to="/client/loading" replace /> },
  { path: "*", element: <Navigate to="/" replace /> },
]);
