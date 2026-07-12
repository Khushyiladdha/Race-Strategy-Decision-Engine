import type { Compound } from './tyres'

export interface Stint {
  compound: Compound
  startLap: number // inclusive, 1-based
  endLap: number // inclusive
}

// Reconstruct stints from a strategy's pit laps + compound sequence, mirroring the backend
// `_build`: bounds = [0, ...pitLaps, totalLaps]; stint i spans bounds[i]+1 .. bounds[i+1].
export function stintsFromStrategy(
  pitLaps: number[],
  compounds: string[],
  totalLaps: number,
): Stint[] {
  const bounds = [0, ...pitLaps, totalLaps]
  return compounds.map((compound, i) => ({
    compound: compound as Compound,
    startLap: bounds[i] + 1,
    endLap: bounds[i + 1],
  }))
}
