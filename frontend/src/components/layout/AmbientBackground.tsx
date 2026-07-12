// Very restrained ambient lighting: a faint purple bloom top-right (near the hero win-probability)
// and a fainter cyan bloom bottom-left. Fixed, blurred, and low-opacity so it reads as depth, not
// decoration. Colors come from the reserved accents via CSS vars — no hard-coded hex.
export function AmbientBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden="true">
      <div
        className="absolute -top-40 right-[-10rem] h-[540px] w-[540px] rounded-full opacity-[0.06] blur-3xl"
        style={{ background: 'radial-gradient(circle, var(--color-fastest), transparent 70%)' }}
      />
      <div
        className="absolute bottom-[-12rem] left-[-10rem] h-[460px] w-[460px] rounded-full opacity-[0.05] blur-3xl"
        style={{ background: 'radial-gradient(circle, var(--color-gain), transparent 70%)' }}
      />
    </div>
  )
}
