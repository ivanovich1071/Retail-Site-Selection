import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface UIState {
  sidebarCollapsed: boolean;
  analysisPanelOpen: boolean;
  activeModal: string | null;
}

const initialState: UIState = {
  sidebarCollapsed: false,
  analysisPanelOpen: false,
  activeModal: null,
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    toggleSidebar(state) { state.sidebarCollapsed = !state.sidebarCollapsed; },
    setAnalysisPanelOpen(state, action: PayloadAction<boolean>) {
      state.analysisPanelOpen = action.payload;
    },
    openModal(state, action: PayloadAction<string>) { state.activeModal = action.payload; },
    closeModal(state) { state.activeModal = null; },
  },
});

export const { toggleSidebar, setAnalysisPanelOpen, openModal, closeModal } = uiSlice.actions;
export default uiSlice.reducer;
