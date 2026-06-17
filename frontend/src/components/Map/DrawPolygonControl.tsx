/**
 * DrawPolygonControl — SVG overlay for freehand polygon drawing on the map.
 *
 * Usage:
 *   - active=true  → capture clicks, draw polygon
 *   - Single click → add vertex
 *   - Double-click → close polygon, call onComplete with GeoJSON Polygon
 *   - Escape or onCancel → discard
 *
 * The component sits on top of the map div. To convert pixel→geo coords
 * it calls mapRef.current.unproject([x, y]) from 2GIS MapGL.
 */
import React, { useCallback, useEffect, useRef, useState } from "react";
import { Button, Tooltip } from "antd";
import { CloseOutlined, CheckOutlined } from "@ant-design/icons";

interface Props {
  active: boolean;
  mapRef: React.MutableRefObject<any | null>;
  onComplete: (polygon: GeoJSON.Polygon) => void;
  onCancel: () => void;
}

interface Point {
  x: number;  // screen pixel
  y: number;
  lon: number;
  lat: number;
}

export default function DrawPolygonControl({ active, mapRef, onComplete, onCancel }: Props) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [points, setPoints] = useState<Point[]>([]);
  const [mouse, setMouse] = useState<{ x: number; y: number } | null>(null);

  // Convert container-relative pixel to geo using 2GIS MapGL unproject
  const pixelToGeo = useCallback((x: number, y: number): [number, number] | null => {
    const map = mapRef.current;
    if (!map) return null;
    try {
      const geo = map.unproject([x, y]);
      return geo as [number, number]; // [lon, lat]
    } catch {
      return null;
    }
  }, [mapRef]);

  const getRelativePos = (e: React.MouseEvent | MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return null;
    return { x: e.clientX - rect.left, y: e.clientY - rect.top };
  };

  const handleClick = useCallback((e: MouseEvent) => {
    if (!active) return;
    e.stopPropagation();
    const pos = getRelativePos(e);
    if (!pos) return;

    // Close polygon on click near first point (within 12px)
    if (points.length >= 3) {
      const first = points[0];
      const dist = Math.hypot(pos.x - first.x, pos.y - first.y);
      if (dist < 14) {
        closePolygon();
        return;
      }
    }

    const geo = pixelToGeo(pos.x, pos.y);
    if (!geo) return;
    setPoints((prev) => [...prev, { x: pos.x, y: pos.y, lon: geo[0], lat: geo[1] }]);
  }, [active, points, pixelToGeo]);

  const handleDblClick = useCallback((e: MouseEvent) => {
    if (!active || points.length < 3) return;
    e.stopPropagation();
    e.preventDefault();
    closePolygon();
  }, [active, points]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!active) return;
    const pos = getRelativePos(e);
    if (pos) setMouse(pos);
  }, [active]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === "Escape") { reset(); onCancel(); }
    if ((e.key === "Enter" || e.key === "Return") && points.length >= 3) closePolygon();
  }, [points, onCancel]);

  function closePolygon() {
    if (points.length < 3) return;
    const coords = points.map((p) => [p.lon, p.lat] as [number, number]);
    coords.push(coords[0]); // close ring
    onComplete({ type: "Polygon", coordinates: [coords] });
    reset();
  }

  function reset() {
    setPoints([]);
    setMouse(null);
  }

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
  }, [active, handleClick, handleDblClick, handleMouseMove, handleKeyDown]);

  // Build SVG path from current points + rubber-band line to mouse
  const allPoints = mouse && points.length > 0
    ? [...points.map((p) => [p.x, p.y]), [mouse.x, mouse.y]]
    : points.map((p) => [p.x, p.y]);

  const polylineD = allPoints.length > 1
    ? allPoints.map((p, i) => `${i === 0 ? "M" : "L"}${p[0]},${p[1]}`).join(" ")
    : "";

  const polygonPoints = points.map((p) => `${p.x},${p.y}`).join(" ");

  if (!active) return null;

  return (
    <div
      ref={containerRef}
      style={{
        position: "absolute", inset: 0, zIndex: 5,
        cursor: points.length >= 3 ? "crosshair" : "crosshair",
        userSelect: "none",
      }}
    >
      <svg
        ref={svgRef}
        width="100%" height="100%"
        style={{ position: "absolute", inset: 0, pointerEvents: "none" }}
      >
        {/* Filled polygon (closed area) */}
        {points.length >= 3 && (
          <polygon
            points={polygonPoints}
            fill="rgba(26, 82, 118, 0.18)"
            stroke="#1a5276"
            strokeWidth={2}
            strokeDasharray="6 3"
          />
        )}

        {/* Rubber-band line */}
        {polylineD && (
          <path
            d={polylineD}
            fill="none"
            stroke="#1a5276"
            strokeWidth={1.5}
            strokeDasharray="6 3"
            opacity={0.8}
          />
        )}

        {/* Vertex circles */}
        {points.map((p, i) => (
          <circle
            key={i}
            cx={p.x} cy={p.y} r={i === 0 ? 7 : 5}
            fill={i === 0 ? "#e74c3c" : "#1a5276"}
            stroke="#fff" strokeWidth={2}
            style={{ cursor: i === 0 && points.length >= 3 ? "pointer" : "default" }}
          />
        ))}
      </svg>

      {/* Control buttons — top-right corner */}
      <div style={{
        position: "absolute", top: 8, right: 8,
        display: "flex", gap: 6, flexDirection: "column",
      }}>
        <div style={{
          background: "#1a5276", color: "#fff",
          borderRadius: 6, padding: "6px 10px",
          fontSize: 12, textAlign: "center", maxWidth: 180,
        }}>
          {points.length === 0 && "Кликайте на карте чтобы добавить точки"}
          {points.length === 1 && "Добавьте ещё точки"}
          {points.length === 2 && "Добавьте ещё точку"}
          {points.length >= 3 && `${points.length} точек · Двойной клик или ↵ чтобы завершить`}
        </div>
        {points.length >= 3 && (
          <Tooltip title="Завершить полигон (Enter)">
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
