import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import App from "./App";
import { registerPwa } from "./pwa";
if (import.meta.env.PROD) registerPwa().catch(() => {});
createRoot(document.getElementById("root")).render(<App />);
