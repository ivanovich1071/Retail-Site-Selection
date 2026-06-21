import React from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";
import { store } from "./store";
import App from "./App";
import ErrorBoundary from "./components/ErrorBoundary";
import { logger } from "./utils/logger";
import "./styles/global.css";

// Global capture of uncaught errors and unhandled promise rejections.
window.addEventListener("error", (e) => {
  logger.error(`Uncaught error: ${e.message}`, {
    source: e.filename,
    line: e.lineno,
    col: e.colno,
  });
});
window.addEventListener("unhandledrejection", (e) => {
  const reason: any = e.reason;
  logger.error(`Unhandled promise rejection: ${reason?.message || String(reason)}`, {
    stack: reason?.stack?.split("\n").slice(0, 3).join(" | "),
  });
});

logger.info("Frontend booted");

// StrictMode disabled: Leaflet is an imperative SDK that misbehaves under
// StrictMode's double-mount (map cleanup leaves the canvas unrecoverable).
ReactDOM.createRoot(document.getElementById("root")!).render(
  <Provider store={store}>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </Provider>
);
