import { useEffect, useImperativeHandle, useRef, forwardRef } from "react";
import type { Map, Marker, MapOptions } from "@2gis/mapgl/global";
import { useAppDispatch, useAppSelector } from "../../hooks/redux";
import {
  setSelectedCoords, setAnalysisLoading, setAnalysisResult,
  setAnalysisError, setCenter, setZoom,
} from "../../store/mapSlice";
import { setAnalysisPanelOpen } from "../../store/uiSlice";
import { analyzeByAddress } from "../../services/api";

const TWOGIS_KEY = import.meta.env.VITE_TWOGIS_KEY || "";

let mapglPromise: Promise<typeof import("@2gis/mapgl/global")> | null = null;

function loadMapGL() {
  if (!mapglPromise) {
    mapglPromise = import("@2gis/mapgl").then((m) => (m as any).load());
  }
  return mapglPromise;
}

export interface MapboxMapHandle {
  getMap: () => Map | null;
}

interface Props {
  onMapReady?: (map: Map) => void;
  drawMode?: boolean;
}

const MapboxMap = forwardRef<MapboxMapHandle, Props>(function MapboxMap(
  { onMapReady, drawMode = false },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const markerRef = useRef<Marker | null>(null);
  const isoLayersRef = useRef<string[]>([]);
  const drawModeRef = useRef(drawMode);

  const dispatch = useAppDispatch();
  const { center, zoom, analysisResult, activeLayer } = useAppSelector((s) => s.map);

  const STYLE_MAP: Record<string, string> = {
    scheme:    "https://mapgl.2gis.com/api/styles/main",
    satellite: "https://mapgl.2gis.com/api/styles/satellite",
    hybrid:    "https://mapgl.2gis.com/api/styles/hybrid",
  };

  // Keep drawModeRef in sync so the click handler closure sees the latest value
  useEffect(() => { drawModeRef.current = drawMode; }, [drawMode]);

  // Expose the internal map instance via ref
  useImperativeHandle(ref, () => ({
    getMap: () => mapRef.current,
  }));

  // Initialise map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    let cancelled = false;

    loadMapGL().then((mapglAPI) => {
      if (cancelled || !containerRef.current) return;

      const map: Map = new mapglAPI.Map(containerRef.current, {
        center: center as [number, number],
        zoom,
        key: TWOGIS_KEY,
        lang: "ru",
      } as MapOptions);

      // Click → analyse address (only when NOT in draw mode)
      map.on("click", async (e: any) => {
        if (drawModeRef.current) return;

        const [lon, lat] = e.lngLat as [number, number];
        dispatch(setSelectedCoords({ lon, lat }));
        dispatch(setAnalysisLoading(true));
        dispatch(setAnalysisPanelOpen(true));

        if (markerRef.current) markerRef.current.destroy();
        markerRef.current = new mapglAPI.Marker(map, {
          coordinates: [lon, lat],
        });

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
        dispatch(setCenter([c[0], c[1]]));
        dispatch(setZoom(map.getZoom()));
      });

      mapRef.current = map;
      onMapReady?.(map);
    }).catch(console.error);

    return () => {
      cancelled = true;
      if (markerRef.current) { markerRef.current.destroy(); markerRef.current = null; }
      if (mapRef.current) { mapRef.current.destroy(); mapRef.current = null; }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Switch base layer style
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const styleUrl = STYLE_MAP[activeLayer] ?? STYLE_MAP.scheme;
    (map as any).setStyle?.(styleUrl);
  }, [activeLayer]); // eslint-disable-line react-hooks/exhaustive-deps

  // Draw isochrone polygons when analysis result arrives
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !analysisResult?.isochrones?.length) return;

    isoLayersRef.current.forEach((id) => {
      try { (map as any).removeLayer(id); } catch {}
    });
    isoLayersRef.current = [];

    const colours = ["#27ae60", "#f39c12", "#e74c3c"];

    analysisResult.isochrones.forEach((iso: any, i: number) => {
      if (!iso.geometry?.coordinates) return;
      const id = `isochrone-fill-${i}`;

      (map as any).addLayer({
        id,
        type: "polygon",
        style: {
          color: colours[i % colours.length],
          opacity: 0.18,
          strokeColor: colours[i % colours.length],
          strokeWidth: 2,
          strokeOpacity: 0.7,
        },
        geometry: iso.geometry.coordinates,
      });

      isoLayersRef.current.push(id);
    });
  }, [analysisResult]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%" }}
    />
  );
});

export default MapboxMap;
