import { useEffect, useRef } from "react";
import L from "leaflet";
import { h3Polyfill } from "../../services/api";

interface Props {
  map: L.Map | null;
  visible: boolean;
  resolution?: number;
}

/**
 * Renders H3 cells covering the current map viewport as a Leaflet layer.
 * Re-fetches (debounced) on pan/zoom while visible.
 */
export default function HexLayer({ map, visible, resolution = 8 }: Props) {
  const layerRef = useRef<L.GeoJSON | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!map) return;

    const clear = () => {
      if (layerRef.current) {
        layerRef.current.remove();
        layerRef.current = null;
      }
    };

    const refresh = async () => {
      if (!visible) return;
      const b = map.getBounds();
      const polygon: GeoJSON.Polygon = {
        type: "Polygon",
        coordinates: [[
          [b.getWest(), b.getSouth()],
          [b.getEast(), b.getSouth()],
          [b.getEast(), b.getNorth()],
          [b.getWest(), b.getNorth()],
          [b.getWest(), b.getSouth()],
        ]],
      };
      try {
        const data = await h3Polyfill(polygon, resolution);
        clear();
        if (!data.geojson) return;
        layerRef.current = L.geoJSON(data.geojson, {
          style: {
            color: "#1a5276",
            weight: 1,
            fillColor: "#1a5276",
            fillOpacity: 0.08,
          },
        }).addTo(map);
      } catch {
        // viewport too large / API error — silently skip
      }
    };

    const onMove = () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(refresh, 500);
    };

    if (visible) {
      refresh();
      map.on("moveend", onMove);
    } else {
      clear();
    }

    return () => {
      map.off("moveend", onMove);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      clear();
    };
  }, [map, visible, resolution]);

  return null;
}
