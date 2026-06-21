import axios from "axios";

// Use relative path so Vite proxy handles CORS in dev;
// in production a reverse proxy (nginx) serves the same origin.
export const api = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

// Inject JWT token into every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── Analysis ──────────────────────────────────────────────
export const analyzeByAddress = (payload: {
  address: string;
  area_sqm?: number;
  parking_spaces?: number;
  visibility_score?: number;
  isochrone_minutes?: number[];
  include_huff?: boolean;
}) => api.post("/analysis/by-address", payload).then((r) => r.data);

export const analyzeByPolygon = (payload: {
  polygon: GeoJSON.Polygon;
  area_sqm?: number;
  parking_spaces?: number;
  visibility_score?: number;
  isochrone_minutes?: number[];
  include_huff?: boolean;
}) => api.post("/analysis/by-polygon", payload).then((r) => r.data);

// ── Job-based analysis ────────────────────────────────────
export interface AnalysisJob {
  id: number;
  location_id: number | null;
  status: string;
  progress_pct: number;
  current_stage: string | null;
  error_message: string | null;
  result: any | null;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

export const startAnalysis = (payload: {
  address?: string;
  polygon?: GeoJSON.Polygon;
  area_sqm?: number;
  parking_spaces?: number;
  visibility_score?: number;
  isochrone_minutes?: number[];
  include_huff?: boolean;
  location_id?: number;
}) => api.post<AnalysisJob>("/analysis/start", payload).then((r) => r.data);

export const getAnalysisJob = (jobId: number) =>
  api.get<AnalysisJob>(`/analysis/jobs/${jobId}`).then((r) => r.data);

export const listAnalysisJobs = (params?: { location_id?: number; limit?: number }) =>
  api.get("/analysis/jobs", { params }).then((r) => r.data);

export const recalculateJob = (jobId: number) =>
  api.post<AnalysisJob>(`/analysis/jobs/${jobId}/recalculate`).then((r) => r.data);

// ── Locations ─────────────────────────────────────────────
export const getLocations = (params?: Record<string, any>) =>
  api.get("/locations", { params }).then((r) => r.data);

export const getLocation = (id: number) =>
  api.get(`/locations/${id}`).then((r) => r.data);

export const createLocation = (body: Record<string, any>) =>
  api.post("/locations", body).then((r) => r.data);

export const updateLocation = (id: number, body: Record<string, any>) =>
  api.patch(`/locations/${id}`, body).then((r) => r.data);

export const updateLocationStatus = (id: number, status: string, comment?: string) =>
  api.patch(`/locations/${id}/status`, { status, comment }).then((r) => r.data);

export const deleteLocation = (id: number) => api.delete(`/locations/${id}`);

// ── Batch ────────────────────────────────────────────────
export const uploadBatchFile = (file: File) => {
  const form = new FormData();
  form.append("file", file);
  return api.post("/batch/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
  }).then((r) => r.data);
};

export const getBatchJobs = () => api.get("/batch").then((r) => r.data);

export const getBatchResults = (jobId: number, page = 1) =>
  api.get(`/batch/${jobId}`, { params: { page } }).then((r) => r.data);

// ── Reports ──────────────────────────────────────────────
export const generateReport = (locationId: number) =>
  api.post(`/reports/${locationId}/generate`).then((r) => r.data);

export const downloadReportUrl = (locationId: number) =>
  `${api.defaults.baseURL}/reports/${locationId}/download`;

// ── Config ──────────────────────────────────────────────
export const getConfig = () =>
  api.get("/config/scoring-weights").then((r) => r.data);

export const updateConfig = (body: Record<string, any>) =>
  api.patch("/config/scoring-weights", body).then((r) => r.data);

// ── H3 Spatial ──────────────────────────────────────────
export const h3Polyfill = (polygon: GeoJSON.Polygon, resolution = 9) =>
  api.post("/h3/polyfill", { polygon, resolution }).then((r) => r.data);

export const h3GetCell = (h3Index: string) =>
  api.get(`/h3/cell/${h3Index}`).then((r) => r.data);

export const h3GetNeighbors = (h3Index: string, k = 1) =>
  api.get(`/h3/neighbors/${h3Index}`, { params: { k } }).then((r) => r.data);

// ── Competition Intelligence (Phase 4) ──────────────────
export const competitionOverlap = (zones: any[]) =>
  api.post("/competition/overlap", { zones }).then((r) => r.data.result);

export const competitionCannibalization = (candidate: any, own_stores: any[]) =>
  api.post("/competition/cannibalization", { candidate, own_stores }).then((r) => r.data.result);

export const competitionWhiteSpace = (cells: any[], min_score = 40, limit?: number) =>
  api.post("/competition/white-space", { cells, min_score, limit }).then((r) => r.data.result);

export const competitionMarketGraph = (stores: any[], min_overlap = 0.05) =>
  api.post("/competition/market-graph", { stores, min_overlap }).then((r) => r.data.result);

// ── Mobility Engine (Phase 5) ───────────────────────────
export const mobilityClean = (points: any[]) =>
  api.post("/mobility/clean", { points }).then((r) => r.data.result);

export const mobilityStaypoints = (points: any[], max_dist_m = 50, min_duration_s = 300) =>
  api.post("/mobility/staypoints", { points, max_dist_m, min_duration_s }).then((r) => r.data.result);

export const mobilityODMatrix = (trips: any[][], resolution = 8) =>
  api.post("/mobility/od-matrix", { trips, resolution }).then((r) => r.data.result);

export const mobilityFootfall = (trajectories: any[][], lat: number, lon: number, radius_m = 100) =>
  api.post("/mobility/footfall", { trajectories, lat, lon, radius_m }).then((r) => r.data.result);

// ── Feature Store (Phase 6) ─────────────────────────────
export const featureRegistry = (group?: string) =>
  api.get("/features/registry", { params: { group } }).then((r) => r.data);

export const buildFeatureVector = (raw: Record<string, any>, entity_id?: string) =>
  api.post("/features/vector", { raw, entity_id }).then((r) => r.data);
