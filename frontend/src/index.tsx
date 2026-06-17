import React from "react";
import ReactDOM from "react-dom/client";
import { Provider } from "react-redux";
import { store } from "./store";
import App from "./App";
import "./styles/global.css";

// StrictMode disabled: 2GIS MapGL is an imperative SDK that breaks
// under StrictMode's double-mount behaviour (map.destroy() on cleanup
// leaves the canvas in an unrecoverable state on re-mount).
ReactDOM.createRoot(document.getElementById("root")!).render(
  <Provider store={store}>
    <App />
  </Provider>
);
