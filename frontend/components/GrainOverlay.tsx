export default function GrainOverlay() {
  return (
    <svg className="grain-overlay" aria-hidden="true">
      <filter id="site-noise">
        <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="4" stitchTiles="stitch" />
      </filter>
      <rect width="100%" height="100%" filter="url(#site-noise)" />
    </svg>
  );
}
