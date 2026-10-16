/**
 * Synthetic trip map view for the RydeResolve demo.
 * Renders a stylised map card with pickup/dropoff markers and a route line.
 * This is not a real map — it uses SVG to avoid external API keys and keep
 * the demo self-contained.
 */
export default function MapView({ trip, height = 180 }) {
  if (!trip) return null;
  const width = 320;
  const pad = 24;

  // Project lat/lng into SVG coordinates (simple equirectangular)
  const xs = [trip.pickup_lng, trip.dropoff_lng];
  const ys = [trip.pickup_lat, trip.dropoff_lat];
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);

  function scale(lng, lat) {
    const x =
      xs.length === 1
        ? width / 2
        : pad + ((lng - minX) / (maxX - minX || 1)) * (width - pad * 2);
    const y =
      ys.length === 1
        ? height / 2
        : height - (pad + ((lat - minY) / (maxY - minY || 1)) * (height - pad * 2));
    return { x, y };
  }

  const pickup = scale(trip.pickup_lng, trip.pickup_lat);
  const dropoff = scale(trip.dropoff_lng, trip.dropoff_lat);

  // Add a slight curve to the route line
  const midX = (pickup.x + dropoff.x) / 2;
  const midY = (pickup.y + dropoff.y) / 2;
  const controlX = midX + (dropoff.y - pickup.y) * 0.15;
  const controlY = midY - (dropoff.x - pickup.x) * 0.15;

  return (
    <div className="trip-map-card" style={{ height }}>
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(200,200,200,0.35)" strokeWidth="0.5" />
          </pattern>
        </defs>
        <rect width={width} height={height} fill="url(#grid)" />
        {/* Streets — decorative background blocks */}
        <g opacity="0.25">
          <rect x={width * 0.15} y={height * 0.1} width={width * 0.7} height={height * 0.08} rx="4" fill="#d8d8d8" />
          <rect x={width * 0.05} y={height * 0.45} width={width * 0.9} height={height * 0.06} rx="4" fill="#d8d8d8" />
          <rect x={width * 0.25} y={height * 0.75} width={width * 0.5} height={height * 0.08} rx="4" fill="#d8d8d8" />
        </g>
        {/* Route line */}
        <path
          d={`M ${pickup.x} ${pickup.y} Q ${controlX} ${controlY} ${dropoff.x} ${dropoff.y}`}
          fill="none"
          stroke="var(--pink)"
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray="6 4"
        />
        {/* Pickup marker */}
        <g transform={`translate(${pickup.x},${pickup.y})`}>
          <circle r="10" fill="var(--pink)" opacity="0.18" />
          <circle r="5" fill="var(--pink)" stroke="white" strokeWidth="2" />
        </g>
        {/* Dropoff marker */}
        <g transform={`translate(${dropoff.x},${dropoff.y})`}>
          <circle r="10" fill="#1a1528" opacity="0.12" />
          <circle r="5" fill="#1a1528" stroke="white" strokeWidth="2" />
        </g>
      </svg>
      <div className="trip-map-legend">
        <span className="trip-map-pin pickup">{trip.pickup_location}</span>
        <span className="trip-map-arrow">→</span>
        <span className="trip-map-pin dropoff">{trip.dropoff_location}</span>
      </div>
    </div>
  );
}
