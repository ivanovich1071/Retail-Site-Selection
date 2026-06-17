import { createSlice, PayloadAction } from "@reduxjs/toolkit";

interface MapState {
  center: [number, number];
  zoom: number;
  selectedCoords: { lon: number; lat: number } | null;
  analysisResult: any | null;
  analysisLoading: boolean;
  analysisError: string | null;
  activeLayer: "scheme" | "satellite" | "hybrid";
  drawMode: boolean;
}

const initialState: MapState = {
  center: [27.5615, 53.9006], // Minsk
  zoom: 12,
  selectedCoords: null,
  analysisResult: null,
  analysisLoading: false,
  analysisError: null,
  activeLayer: "scheme",
  drawMode: false,
};

const mapSlice = createSlice({
  name: "map",
  initialState,
  reducers: {
    setCenter(state, action: PayloadAction<[number, number]>) {
      state.center = action.payload;
    },
    setZoom(state, action: PayloadAction<number>) {
      state.zoom = action.payload;
    },
    setSelectedCoords(state, action: PayloadAction<{ lon: number; lat: number } | null>) {
      state.selectedCoords = action.payload;
    },
    setAnalysisResult(state, action: PayloadAction<any>) {
      state.analysisResult = action.payload;
      state.analysisLoading = false;
      state.analysisError = null;
    },
    setAnalysisLoading(state, action: PayloadAction<boolean>) {
      state.analysisLoading = action.payload;
    },
    setAnalysisError(state, action: PayloadAction<string | null>) {
      state.analysisError = action.payload;
      state.analysisLoading = false;
    },
    toggleLayer(state) {
      const cycle: Array<"scheme" | "satellite" | "hybrid"> = ["scheme", "satellite", "hybrid"];
      const idx = cycle.indexOf(state.activeLayer as any);
      state.activeLayer = cycle[(idx + 1) % cycle.length];
    },
    setActiveLayer(state, action: PayloadAction<"scheme" | "satellite" | "hybrid">) {
      state.activeLayer = action.payload;
    },
    setDrawMode(state, action: PayloadAction<boolean>) {
      state.drawMode = action.payload;
    },
    clearAnalysis(state) {
      state.analysisResult = null;
      state.selectedCoords = null;
      state.analysisError = null;
    },
  },
});

export const {
  setCenter, setZoom, setSelectedCoords, setAnalysisResult,
  setAnalysisLoading, setAnalysisError, toggleLayer, setActiveLayer, setDrawMode, clearAnalysis,
} = mapSlice.actions;
export default mapSlice.reducer;
