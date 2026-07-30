import {useMap} from "react-leaflet";
import {useEffect} from "react";

/**
 * Leaflet measures its container size once, on mount. Calcite's web
 * components upgrade asynchronously, so the surrounding flex layout can
 * still be settling after the map has already initialized — leaving the
 * map too small until something (e.g. a manual window resize) forces a
 * recalculation. This watches the container and nudges Leaflet whenever
 * it changes size, including right after mount.
 */
export default function ResizeHandler() {
  const map = useMap();

  useEffect(() => {
    const container = map.getContainer();

    const raf = requestAnimationFrame(() => map.invalidateSize());

    const resizeObserver = new ResizeObserver(() => map.invalidateSize());
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(raf);
      resizeObserver.disconnect();
    };
  }, [map]);

  return null;
}
