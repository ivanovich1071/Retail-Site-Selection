import { useEffect, useRef, forwardRef, useImperativeHandle } from "react";
import { load } from "@2gis/mapgl";
import type { Map, Marker } from "@2gis/mapgl/global";
import { useAppDispatch, useAppSelector } from "../../hooks/redux";
import {
  setSelectedCoords, setAnalysisLoading, setAnalysisResult,
  setAnalysisError, setCenter, setZoom,
} from "../../store/mapSlice";
import { setAnalysisPanelOpen } from "../../store/uiSlice";
import { analyzeByAddress } from "../../services/api";

const TWOGIS_KEY = import.meta.env.VITE_TWOGIS_KEY as string;

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
  const containerRef  = useRef<HTMLDivElement>(null);
  const mapRef        = useRef<Map | null>(null);
  const markerRef     = useRef<Marker | null>(null);
  const isoLayersRef  = useRef<string[]>([]);
  const drawModeRef   = useRef(drawMode);
  const destroyedRef  = useRef(false);

  const dispatch = useAppDispatch();
  const { center, zoom, analysisResult, activeLayer } = useAppSelector((s) => s.map);

  useEffect(() => { drawModeRef.current = drawMode; }, [drawMode]);
  useImperativeHandle(ref, () => ({ getMap: () => mapRef.current }));

  // ── Init map ──────────────────────────────────────────────────────
  useEffect(() => {
    if (mapRef.current || destroyedRef.current) return;

    let cancelled = false;

    load().then((mapgl) => {
      if (cancelled || !containerRef.current || mapRef.current) return;

      const map = new mapgl.Map(containerRef.current, {
        center: center as [number, number],
        zoom,
        key: TWOGIS_KEY || "",
        lang: "ru",
      });

      map.on("click", async (e: any) => {
        if (drawModeRef.current) return;
        const [lon, lat] = e.lngLat as [number, number];
        dispatch(setSelectedCoords({ lon, lat }));
        dispatch(setAnalysisLoading(true));
        dispatch(setAnalysisPanelOpen(true));

        if (markerRef.current) { markerRef.current.destroy(); }
        markerRef.current = new mapgl.Marker(map, { coordinates: [lon, lat] });

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
    }).catch((err) => {
      console.error("2GIS MapGL load error:", err);
    });

    return () => {
      cancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Cleanup on unmount ───────────────────────────────────────────
  useEffect(() => {
    return () => {
      destroyedRef.current = true;
      if (markerRef.current) { markerRef.current.destroy(); markerRef.current = null; }
      if (mapRef.current)    { mapRef.current.destroy();    mapRef.current = null; }
    };
  }, []);

  // ── Switch layer style ───────────────────────────────────────────
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const STYLES: Record<string, string> = {
      scheme:    "https://mapgl.2gis.com/api/styles/main",
      satellite: "https://mapgl.2gis.com/api/styles/satellite",
      hybrid:    "https://mapgl.2gis.com/api/styles/hybrid",
    };
    try { (map as any).setStyle?.(STYLES[activeLayer] ?? STYLES.scheme); } catch {}
  }, [activeLayer]);

  // ── Draw isochrone polygons ──────────────────────────────────────
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
      const id = `iso-fill-${i}`;
      try {
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
      } catch {}
    });
  }, [analysisResult]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", minHeight: "500px" }}
    />
  );
});

export default MapboxMap;
