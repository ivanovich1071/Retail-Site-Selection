import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button, Tooltip } from "antd";
import { CloseOutlined, CheckOutlined } from "@ant-design/icons";
import L from "leaflet";

interface Props {
  active: boolean;
  mapRef: React.MutableRefObject<L.Map | null>;
  onComplete: (polygon: GeoJSON.Polygon) => void;
  onCancel: () => void;
}

interface Point {
  x: number;
  y: number;
  lon: number;
  lat: number;
}

export default function DrawPolygonControl({ active, mapRef, onComplete, onCancel }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef       = useRef<SVGSVGElement>(null);
  const pointsRef    = useRef<Point[]>([]);           // authoritative store
  const [points, setPoints]   = useState<Point[]>([]); // for rendering only
  const [mouse, setMouse]     = useState<{ x: number; y: number } | null>(null);

  const pixelToGeo = (x: number, y: number): [number, number] | null => {
    const map = mapRef.current;
    if (!map || !containerRef.current) return null;
    try {
      const rect = containerRef.current.getBoundingClientRect();
      const latlng = map.containerPointToLatLng(
        L.point(x, y - (rect.top - (map.getContainer()?.getBoundingClientRect().top ?? 0)))
      );
      return [latlng.lng, latlng.lat];
    } catch { return null; }
  };

  const getPos = (e: MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return null;
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const reset = useCallback(() => {
    pointsRef.current = [];
    setPoints([]);
    setMouse(null);
  }, []);

  const closePolygon = useCallback(() => {
    const pts = pointsRef.current;
    if (pts.length < 3) return;
    const coords = pts.map((p) => [p.lon, p.lat] as [number, number]);
    coords.push(coords[0]);
    onComplete({ type: "Polygon", coordinates: [coords] });
    reset();
  }, [onComplete, reset]);

  // All handlers use refs — no dependency on `points` state
  const handleClick = useCallback((e: MouseEvent) => {
    if (!active) return;
    e.stopPropagation();
    const pos = getPos(e);
    if (!pos) return;

    const pts = pointsRef.current;
    if (pts.length >= 3) {
      const first = pts[0];
      if (Math.hypot(pos.x - first.x, pos.y - first.y) < 14) {
        closePolygon();
        return;
      }
    }

    const geo = pixelToGeo(pos.x, pos.y);
    if (!geo) return;
    const newPts = [...pts, { x: pos.x, y: pos.y, lon: geo[0], lat: geo[1] }];
    pointsRef.current = newPts;
    setPoints([...newPts]);
  }, [active, closePolygon]); // no `points` dep!

  const handleDblClick = useCallback((e: MouseEvent) => {
    if (!active || pointsRef.current.length < 3) return;
    e.stopPropagation();
    e.preventDefault();
    closePolygon();
  }, [active, closePolygon]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!active) return;
    const pos = getPos(e);
    if (pos) setMouse(pos);
  }, [active]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") { reset(); onCancel(); }
    if ((e.key === "Enter" || e.key === "Return") && pointsRef.current.length >= 3) closePolygon();
  }, [reset, onCancel, closePolygon]);

  useEffect(() => {
    if (!active) { reset(); return; }
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("click", handleClick);
    el.addEventListener("dblclick", handleDblClick);
    el.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      el.removeEventListener("click", handleClick);
      el.removeEventListener("dblclick", handleDblClick);
      el.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [active, handleClick, handleDblClick, handleMouseMove, handleKeyDown, reset]);

  const allPts = mouse && points.length > 0
    ? [...points.map((p) => [p.x, p.y]), [mouse.x, mouse.y]]
    : points.map((p) => [p.x, p.y]);

  const polylineD = allPts.length > 1
    ? allPts.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ")
    : "";

  if (!active) return null;

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute", inset: 0, zIndex: 500,
        cursor: "crosshair", userSelect: "none",
      }}
    >
      <svg
        ref={svgRef}
        width="100%" height="100%"
        style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      >
        {points.length >= 3 && (
          <polygon
            points={points.map((p) => `${p.x},${p.y}`).join(" ")}
            fill="rgba(26,82,118,0.15)"
            stroke="#1a5276"
            strokeWidth={2}
            strokeDasharray="6 3"
          />
        )}
        {polylineD && (
          <path
            d={polylineD}
            fill="none"
            stroke="#1a5276"
            strokeWidth={1.5}
            strokeDasharray="6 3"
            opacity={0.85}
          />
        )}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.x} cy={p.y} r={i === 0 ? 7 : 5}
            fill={i === 0 ? "#e74c3c" : "#1a5276"}
            stroke="#fff" strokeWidth={2}
          />
        ))}
      </svg>

      <div style={{
        position: "absolute", top: 8, right: 8,
        display: "flex", gap: 6, flexDirection: "column", zIndex: 501,
      }}>
        <div style={{
          background: "#1a5276", color: "#fff",
          borderRadius: 6, padding: "6px 10px",
          fontSize: 12, textAlign: "center", maxWidth: 200,
        }}>
          {points.length === 0 && "Кликайте на карте чтобы добавить точки"}
          {points.length === 1 && "Добавьте ещё точки"}
          {points.length === 2 && "Добавьте ещё одну точку"}
          {points.length >= 3 && `${points.length} точек · Двойной клик или ↵ завершить`}
        </div>
        {points.length >= 3 && (
          <Tooltip title="Завершить (Enter)">
            <Button
              type="primary" icon={<CheckOutlined />} size="small"
              onClick={(e) => { e.stopPropagation(); closePolygon(); }}
              style={{ background: "#27ae60", borderColor: "#27ae60" }}
            >
              Готово
            </Button>
          </Tooltip>
        )}
        <Tooltip title="Отмена (Esc)">
          <Button
            icon={<CloseOutlined />} size="small" danger
            onClick={(e) => { e.stopPropagation(); reset(); onCancel(); }}
          >
            Отмена
          </Button>
        </Tooltip>
      </div>
    </div>
  );
}
