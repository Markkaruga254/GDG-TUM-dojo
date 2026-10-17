import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "@/App";
import "@/styles/globals.css";

const container = document.getElementById("root");
if (!container) {
  throw new Error("Root container #root not found in index.html");
}

createRoot(container).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
