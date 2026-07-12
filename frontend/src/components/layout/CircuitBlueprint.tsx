// Stylized per-circuit silhouettes — a faint blueprint that changes with the selected track, so
// each circuit has a visual identity WITHOUT spending a palette color (the §4 colors are all
// load-bearing). These are recognizable-in-character motifs, not surveyed geometry; real circuit
// SVGs can drop into this map later. Rendered very faint + blurred so imperfection reads as texture.

const PATHS: Record<string, string> = {
  // compact desert loop with hairpins
  bahrain:
    'M70,150 C70,95 120,78 165,90 C205,100 200,138 240,148 C288,160 300,112 342,126 C372,136 360,182 322,190 C276,200 252,166 205,176 C158,186 168,214 118,208 C80,204 70,186 70,150 Z',
  // rounded loop with a stadium sweep
  spanish:
    'M70,120 C70,82 118,70 168,82 L286,104 C334,114 350,152 314,178 C284,200 240,182 200,188 C150,196 92,204 74,162 C67,146 68,132 70,120 Z',
  // few long straights, three big corners
  austrian:
    'M74,196 L156,92 C166,79 188,79 199,94 L312,184 C325,195 318,210 300,210 L92,210 C75,210 68,205 74,196 Z',
  // boxy street circuit, right angles
  singapore:
    'M64,84 L322,84 L322,132 L232,132 L232,170 L344,170 L344,212 L112,212 L112,152 L64,152 Z',
  // figure-eight crossover
  japanese:
    'M104,92 C44,112 62,182 132,172 C202,162 210,92 282,102 C352,112 342,192 270,192 C192,192 182,112 104,92 Z',
}

const DEFAULT_PATH =
  'M80,150 C80,100 140,90 200,100 C260,110 320,110 320,150 C320,190 260,200 200,190 C140,180 80,200 80,150 Z'

export function CircuitBlueprint({ circuit }: { circuit: string }) {
  const d = PATHS[circuit] ?? DEFAULT_PATH
  return (
    <div className="pointer-events-none absolute inset-0 -z-0 overflow-hidden" aria-hidden="true">
      <svg
        viewBox="30 20 340 240"
        preserveAspectRatio="xMidYMid slice"
        className="h-full w-full opacity-[0.07] blur-[1.5px]"
      >
        <path
          d={d}
          fill="none"
          className="stroke-ink"
          strokeWidth="2.5"
          strokeLinejoin="round"
          strokeLinecap="round"
        />
      </svg>
    </div>
  )
}
