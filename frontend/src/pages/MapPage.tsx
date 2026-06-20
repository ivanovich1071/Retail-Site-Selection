import { useRef, useState, useCallback } from "react";
import { Input, Button, Tooltip, Space, message } from "antd";
import {
  SearchOutlined, AppstoreOutlined,
  DeleteOutlined, SaveOutlined, EditOutlined,
} from "@ant-design/icons";
import { useAppDispatch, useAppSelector } from "../hooks/redux";
import {
  setAnalysisLoading, setAnalysisResult, setAnalysisError,
  toggleLayer, clearAnalysis, setDrawMode,
} from "../store/mapSlice";
import { setAnalysisPanelOpen } from "../store/uiSlice";
import { analyzeByAddress, analyzeByPolygon, createLocation } from "../services/api";
import MapboxMap, { type MapboxMapHandle } from "../components/Map/MapboxMap";
import DrawPolygonControl from "../components/Map/DrawPolygonControl";
import HexLayer from "../components/Map/HexLayer";
import AnalysisDrawer from "../components/Panels/AnalysisDrawer";
import type L from "leaflet";

export default function MapPage() {
  const dispatch   = useAppDispatch();
  const mapHandle  = useRef<MapboxMapHandle>(null);

  // Stable ref that DrawPolygonControl can use — updated via onMapReady
  const stableMapRef = useRef<L.Map | null>(null);

  const [address, setAddress]           = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [saveLoading, setSaveLoading]     = useState(false);
  const [mapInstance, setMapInstance]     = useState<L.Map | null>(null);
  const [hexVisible, setHexVisible]       = useState(false);

  const { analysisResult, activeLayer, drawMode } = useAppSelector((s) => s.map);

  const LAYER_LABELS: Record<string, string> = {
    scheme: "Схема", satellite: "Спутник", hybrid: "Гибрид",
  };

  const handleMapReady = useCallback((map: L.Map) => {
    stableMapRef.current = map;
    setMapInstance(map);
  }, []);

  // ── Address search ────────────────────────────────────────────
  const handleSearch = async () => {
    if (!address.trim()) return;
    setSearchLoading(true);
    dispatch(setAnalysisLoading(true));
    dispatch(setAnalysisPanelOpen(true));
    try {
      const result = await analyzeByAddress({
        address,
        isochrone_minutes: [5, 10, 15],
        include_huff: true,
      });
      dispatch(setAnalysisResult(result));
    } catch (err: any) {
      dispatch(setAnalysisError(err?.response?.data?.detail || "Ошибка анализа"));
    } finally {
      setSearchLoading(false);
    }
  };

  // ── Polygon complete ──────────────────────────────────────────
  const handlePolygonComplete = async (polygon: GeoJSON.Polygon) => {
    dispatch(setDrawMode(false));
    dispatch(setAnalysisLoading(true));
    dispatch(setAnalysisPanelOpen(true));
    try {
      const result = await analyzeByPolygon({
        polygon,
        isochrone_minutes: [5, 10, 15],
        include_huff: true,
      });
      dispatch(setAnalysisResult(result));
    } catch (err: any) {
      dispatch(setAnalysisError(err?.response?.data?.detail || "Ошибка анализа зоны"));
    }
  };

  // ── Save location ─────────────────────────────────────────────
  const handleSave = async () => {
    if (!analysisResult) return;
    setSaveLoading(true);
    try {
      await createLocation({ address: analysisResult.address || "Нарисованная зона" });
      message.success("Объект сохранён");
    } catch {
      message.error("Не удалось сохранить объект");
    } finally {
      setSaveLoading(false);
    }
  };

  return (
    <div className="map-page">
      {/* Toolbar */}
      <div style={{
        position: "absolute", top: 12, left: 12, zIndex: 20,
        background: "#fff", borderRadius: 8, padding: "8px 10px",
        boxShadow: "0 2px 10px rgba(0,0,0,0.18)",
        display: "flex", gap: 8, alignItems: "center",
        flexWrap: "wrap", maxWidth: "calc(100vw - 200px)",
      }}>
        <Input
          placeholder="Введите адрес…"
          value={address}
          onChange={(e) => setAddress(e.target.value)}
          onPressEnter={handleSearch}
          style={{ width: 280 }}
          prefix={<SearchOutlined />}
          disabled={drawMode}
        />
        <Button
          type="primary"
          onClick={handleSearch}
          loading={searchLoading}
          disabled={drawMode || !address.trim()}
        >
          Анализ
        </Button>

        <Tooltip title={drawMode ? "Нажмите Esc или кнопку Отмена чтобы выйти" : "Нарисовать зону анализа на карте"}>
          <Button
            icon={<EditOutlined />}
            type={drawMode ? "primary" : "default"}
            danger={drawMode}
            onClick={() => dispatch(setDrawMode(!drawMode))}
          >
            {drawMode ? "Отмена рисования" : "Нарисовать зону"}
          </Button>
        </Tooltip>

        <Tooltip title="Сменить слой карты">
          <Button icon={<AppstoreOutlined />} onClick={() => dispatch(toggleLayer())}>
            {LAYER_LABELS[activeLayer]}
          </Button>
        </Tooltip>

        <Tooltip title="H3-сетка (гексагоны) для пространственного анализа">
          <Button
            icon={<AppstoreOutlined />}
            type={hexVisible ? "primary" : "default"}
            onClick={() => setHexVisible((v) => !v)}
          >
            H3-сетка
          </Button>
        </Tooltip>

        {analysisResult && !drawMode && (
          <Space>
            <Tooltip title="Сохранить объект">
              <Button icon={<SaveOutlined />} onClick={handleSave} loading={saveLoading} />
            </Tooltip>
            <Tooltip title="Очистить результаты">
              <Button icon={<DeleteOutlined />} danger onClick={() => dispatch(clearAnalysis())} />
            </Tooltip>
          </Space>
        )}
      </div>

      {/* Map + overlay wrapper */}
      <div className="map-container" style={{ position: "relative", flex: 1, height: "100%" }}>
        <MapboxMap
          ref={mapHandle}
          drawMode={drawMode}
          onMapReady={handleMapReady}
        />

        {/* H3 hex grid overlay */}
        <HexLayer map={mapInstance} visible={hexVisible} />

        {/* Polygon lasso overlay */}
        <DrawPolygonControl
          active={drawMode}
          mapRef={stableMapRef}
          onComplete={handlePolygonComplete}
          onCancel={() => dispatch(setDrawMode(false))}
        />
      </div>

      <AnalysisDrawer />
    </div>
  );
}
