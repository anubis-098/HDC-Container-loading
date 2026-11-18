import React from "react";
import ReactDOM from "react-dom/client";
import { RouterProvider } from "react-router-dom";
import { router } from "./app/router";
import "./styles/theme.css";
import "./styles/client.css";
import "./styles/language.css";
import "./styles/shared-ui.css";
import "./styles/header.css";
import "./styles/admin-ui.css";
import "./styles/pallets.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
