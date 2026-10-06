/** The Qualifyr logo mark: a target reticle fused with a magnifier – "find and lock onto
 *  the real buyers". Drawn with currentColor so it inherits whatever text colour it sits in
 *  (brand-foreground inside the brand square, foreground on its own), and stays crisp at any
 *  size instead of the raster a generator would give. */
export function QualifyrMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" fill="none" className={className} role="img" aria-label="Qualifyr">
      <g stroke="currentColor" strokeWidth={5} strokeLinecap="round" strokeLinejoin="round">
        <circle cx="31" cy="30" r="18" />
        <path d="M43.8 42.8 53 52" />
        <path d="M31 7v8M31 45v8M8 30h8M46 30h8" strokeWidth={4} />
      </g>
      <circle cx="31" cy="30" r="5" fill="currentColor" />
    </svg>
  )
}
