import { configureStore } from "@reduxjs/toolkit";
import authReducer from "./authSlice";
import mapReducer from "./mapSlice";
import locationReducer from "./locationSlice";
import uiReducer from "./uiSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    map: mapReducer,
    locations: locationReducer,
    ui: uiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
