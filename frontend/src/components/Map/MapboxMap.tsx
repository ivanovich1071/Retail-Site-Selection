import { useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import type { Map, Marker, MapOptions } from "@2gis/mapgl/global";
import { useAppDispatch, useAppSelector } from "../../hooks/redux";
import {
  setSelectedCoords, setAnalysisLoading, setAnalysisResult,
  setAnalysisError, setCenter, setZoom,
} from "../../store/mapSlice";
import { setAnalysisPanelOpen } from "../../store/uiSlice";
import { analyzeByAddress } from "../../services/api";

const TWOGIS_KEY = import.meta.env.VITE_TWOGIS_KEY as string | undefined;

// Module-level cache — avoids re-loading CDN script on HMR / StrictMode
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
  const mapRef      = useRef<Map | null>(null);
  const markerRef   = useRef<Marker | null>(null);
  const isoLayersRef = useRef<string[]>([]);
  const drawModeRef  = useRef(drawMode);
  // Guard against StrictMode double-invoke creating two maps
  const initStartedRef = useRef(false);

  const dispatch = useAppDispatch();
  const { center, zoom, analysisResult, activeLayer } = useAppSelector((s) => s.map);

  const STYLE_MAP: Record<string, string> = {
    scheme:    "https://mapgl.2gis.com/api/styles/main",
    satellite: "https://mapgl.2gis.com/api/styles/satellite",
    hybrid:    "https://mapgl.2gis.com/api/styles/hybrid",
  };

  useEffect(() => { drawModeRef.current = drawMode; }, [drawMode]);

  useImperativeHandle(ref, () => ({ getMap: () => mapRef.current }));

  // ── Initialise map once ─────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;
    // Already running or already created
    if (initStartedRef.current || mapRef.current) return;
    initStartedRef.current = true;

    let active = true;

    loadMapGL()
      .then((mapglAPI) => {
        if (!active || !containerRef.current) return;

        const map: Map = new mapglAPI.Map(containerRef.current, {
          center: center as [number, number],
          zoom,
          key: TWOGIS_KEY || "",
          lang: "ru",
        } as MapOptions);

        // Click → analyse by coordinates (skip when drawing)
        map.on("click", async (e: any) => {
          if (drawModeRef.current) return;
          const [lon, lat] = e.lngLat as [number, number];
          dispatch(setSelectedCoords({ lon, lat }));
          dispatch(setAnalysisLoading(true));
          dispatch(setAnalysisPanelOpen(true));

          if (markerRef.current) { markerRef.current.destroy(); }
          markerRef.current = new mapglAPI.Marker(map, { coordinates: [lon, lat] });

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
      })
      .catch((err) => {
        console.error("2GIS MapGL load error:", err);
        initStartedRef.current = false; // allow retry
      });

    return () => {
      active = false;
      // Only destroy on true unmount (not StrictMode double-invoke)
      // We use initStartedRef to detect if a real unmount happened
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Cleanup on real unmount (component removed from DOM)
  useEffect(() => {
    return () => {
      if (markerRef.current) { markerRef.current.destroy(); markerRef.current = null; }
      if (mapRef.current)    { mapRef.current.destroy();    mapRef.current = null; }
      initStartedRef.current = false;
    };
  }, []);

  // ── Switch base layer style ─────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    try { (map as any).setStyle?.(STYLE_MAP[activeLayer] ?? STYLE_MAP.scheme); } catch {}
  }, [activeLayer]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Draw isochrone polygons ─────────────────────────────────────────
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
      try {
        (map as any).addLayer({
          id,
          type: "polygon",
          style: {
            color:         colours[i % colours.length],
            opacity:       0.18,
            strokeColor:   colours[i % colours.length],
            strokeWidth:   2,
            strokeOpacity: 0.7,
          },
          geometry: iso.geometry.coordinates,
        });
        isoLayersRef.current.push(id);
      } catch {}
    });
  }, [analysisResult]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", minHeight: 400 }}
    />
  );
});

export default MapboxMap;
