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

// ── Locations ─────────────────────────────────────────────
export const getLocations = (params?: Record<string, any>) =>
  api.get("/locations", { params }).then((r) => r.data);

export const createLocation = (body: Record<string, any>) =>
  api.post("/locations", body).then((r) => r.data);

export const updateLocation = (id: number, body: Record<string, any>) =>
  api.patch(`/locations/${id}`, body).then((r) => r.data);

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
