import { useRef, useState } from "react";
import { Input, Button, Tooltip, Space, message } from "antd";
import {
  SearchOutlined, LayersOutlined,
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
import AnalysisDrawer from "../components/Panels/AnalysisDrawer";

export default function MapPage() {
  const dispatch = useAppDispatch();
  const mapHandle = useRef<MapboxMapHandle>(null);

  const [address, setAddress] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);

  const { analysisResult, activeLayer, drawMode } = useAppSelector((s) => s.map);

  const LAYER_LABELS: Record<string, string> = {
    scheme: "Схема", satellite: "Спутник", hybrid: "Гибрид",
  };

  // ── Address search ─────────────────────────────────────────────────
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

  // ── Polygon draw complete ──────────────────────────────────────────
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

  // ── Save location ─────────────────────────────────────────────────
  const handleSaveLocation = async () => {
    if (!analysisResult) return;
    setSaveLoading(true);
    try {
      await createLocation({ address: analysisResult.address || "Нарисованная зона" });
      message.success("Объект сохранён в базу");
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
        position: "absolute", top: 12, left: 12, zIndex: 10,
        background: "#fff", borderRadius: 8, padding: 8, boxShadow: "0 2px 8px rgba(0,0,0,0.2)",
        display: "flex", gap: 8, alignItems: "center",
        flexWrap: "wrap", maxWidth: "calc(100vw - 24px)",
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
          disabled={drawMode}
        >
          Анализ
        </Button>

        <Tooltip title={drawMode ? "Выйти из режима рисования (Esc)" : "Нарисовать зону на карте"}>
          <Button
            icon={<EditOutlined />}
            type={drawMode ? "primary" : "default"}
            danger={drawMode}
            onClick={() => dispatch(setDrawMode(!drawMode))}
            style={drawMode ? {} : { borderColor: "#1a5276", color: "#1a5276" }}
          >
            {drawMode ? "Отмена рисования" : "Нарисовать зону"}
          </Button>
        </Tooltip>

        <Tooltip title="Переключить слой">
          <Button icon={<LayersOutlined />} onClick={() => dispatch(toggleLayer())}>
            {LAYER_LABELS[activeLayer]}
          </Button>
        </Tooltip>

        {analysisResult && !drawMode && (
          <>
            <Tooltip title="Сохранить объект">
              <Button
                icon={<SaveOutlined />}
                onClick={handleSaveLocation}
                loading={saveLoading}
              />
            </Tooltip>
            <Tooltip title="Очистить">
              <Button
                icon={<DeleteOutlined />}
                danger
                onClick={() => dispatch(clearAnalysis())}
              />
            </Tooltip>
          </>
        )}
      </div>

      {/* Map + draw overlay wrapper */}
      <div className="map-container" style={{ position: "relative" }}>
        <MapboxMap
          ref={mapHandle}
          drawMode={drawMode}
        />

        {/* Polygon lasso overlay — sits above the map */}
        <DrawPolygonControl
          active={drawMode}
          mapRef={{ current: mapHandle.current?.getMap() ?? null }}
          onComplete={handlePolygonComplete}
          onCancel={() => dispatch(setDrawMode(false))}
        />
      </div>

      {/* Right panel */}
      <AnalysisDrawer />
    </div>
  );
}
