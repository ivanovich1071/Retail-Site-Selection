import { useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useAppDispatch, useAppSelector } from "../../hooks/redux";
import {
  setSelectedCoords, setAnalysisLoading, setAnalysisResult,
  setAnalysisError, setCenter, setZoom,
} from "../../store/mapSlice";
import { setAnalysisPanelOpen } from "../../store/uiSlice";
import { analyzeByAddress } from "../../services/api";

// Fix Leaflet default marker icons (broken by bundlers)
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

// Leaflet-compatible map handle (mirrors previous 2GIS interface)
export interface MapboxMapHandle {
  getMap: () => L.Map | null;
}

interface Props {
  onMapReady?: (map: L.Map) => void;
  drawMode?: boolean;
}

const TILE_LAYERS = {
  scheme:    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  satellite: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  hybrid:    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
};

const TILE_ATTRS = {
  scheme:    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
  satellite: "Tiles &copy; Esri",
  hybrid:    "Tiles &copy; Esri",
};

const MapboxMap = forwardRef<MapboxMapHandle, Props>(function MapboxMap(
  { onMapReady, drawMode = false },
  ref,
) {
  const containerRef  = useRef<HTMLDivElement>(null);
  const mapRef        = useRef<L.Map | null>(null);
  const tileLayerRef  = useRef<L.TileLayer | null>(null);
  const markerRef     = useRef<L.Marker | null>(null);
  const isoLayersRef  = useRef<L.Layer[]>([]);
  const drawModeRef   = useRef(drawMode);

  const dispatch = useAppDispatch();
  const { center, zoom, analysisResult, activeLayer } = useAppSelector((s) => s.map);

  useEffect(() => { drawModeRef.current = drawMode; }, [drawMode]);
  useImperativeHandle(ref, () => ({ getMap: () => mapRef.current }));

  // ── Init map once ──────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = L.map(containerRef.current, {
      center: [center[1], center[0]] as [number, number], // Leaflet uses [lat, lon]
      zoom,
      zoomControl: true,
    });

    // Base tile layer
    const tile = L.tileLayer(TILE_LAYERS.scheme, {
      attribution: TILE_ATTRS.scheme,
      maxZoom: 19,
    }).addTo(map);
    tileLayerRef.current = tile;

    map.on("click", async (e: L.LeafletMouseEvent) => {
      if (drawModeRef.current) return;
      const { lat, lng: lon } = e.latlng;
      dispatch(setSelectedCoords({ lon, lat }));
      dispatch(setAnalysisLoading(true));
      dispatch(setAnalysisPanelOpen(true));

      if (markerRef.current) markerRef.current.remove();
      markerRef.current = L.marker([lat, lon]).addTo(map);

      try {
        const result = await analyzeByAddress({
          address: `${lat.toFixed(5)},${lon.toFixed(5)}`,
          isochrone_minutes: [5, 10, 15],
          include_huff: false,
        });
        dispatch(setAnalysisResult(result));
      } catch (err: any) {
        dispatch(setAnalysisError(err?.response?.data?.detail || "Ошибка анализа"));
      }
    });

    map.on("moveend", () => {
      const c = map.getCenter();
      dispatch(setCenter([c.lng, c.lat]));
      dispatch(setZoom(map.getZoom()));
    });

    mapRef.current = map;
    onMapReady?.(map);

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Switch tile layer ─────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (tileLayerRef.current) { tileLayerRef.current.remove(); }
    tileLayerRef.current = L.tileLayer(TILE_LAYERS[activeLayer] ?? TILE_LAYERS.scheme, {
      attribution: TILE_ATTRS[activeLayer] ?? TILE_ATTRS.scheme,
      maxZoom: 19,
    }).addTo(map);
  }, [activeLayer]);

  // ── Draw isochrone polygons ───────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    isoLayersRef.current.forEach((l) => l.remove());
    isoLayersRef.current = [];

    if (!analysisResult?.isochrones?.length) return;

    const colours = ["#27ae60", "#f39c12", "#e74c3c"];
    analysisResult.isochrones.forEach((iso: any, i: number) => {
      if (!iso.geometry?.coordinates) return;
      // GeoJSON Polygon coords are [lon, lat], Leaflet wants [lat, lon]
      const rings = iso.geometry.coordinates.map((ring: [number, number][]) =>
        ring.map(([lon, lat]) => [lat, lon] as [number, number]),
      );
      const poly = L.polygon(rings, {
        color: colours[i % colours.length],
        weight: 2,
        opacity: 0.8,
        fillOpacity: 0.15,
      }).addTo(map);
      isoLayersRef.current.push(poly);
    });
  }, [analysisResult]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", minHeight: 500 }}
    />
  );
});

export default MapboxMap;
