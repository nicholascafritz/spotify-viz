# spotify-viz abstract flow-field center design

## Status and lineage

This document is the approved visual successor to the [original spotify-viz design](2026-08-30-spotify-viz-design.md).

It supersedes only the cathedral composition and focal-void requirements in that document's "Visual fidelity revision — approved" section. The dense side bulkheads remain. All runtime, input, status, signal processing, failure behavior, layout, palette intent, dependencies, packaging, and verification decisions in the original design remain in force.

## Composition

The batgrl scene keeps five persistent truecolor text planes: backdrop, architecture, particles, atmosphere, and reactive.

The architecture plane contains the existing dense, full-height left and right bulkheads. The space between those bulkheads is open: it contains no portal, doorway, box, horizon, floor perspective, catwalk bars, focal axis, or other object-like center geometry.

One continuous abstract particle swarm occupies that open center. Its distribution is meaningful but non-solid, without a singular focal object or rigid boundary. All output remains fixed-size, clipped to the terminal, deterministic for identical inputs, and limited to ASCII glyphs.

## Audio-to-motion mapping

- Quiet audio produces a sparse field of `.` and `:` particles with slow deterministic drift.
- Bass compresses and releases particles around two broad moving cloud centers.
- Midrange bends and laterally shears the flow.
- Treble introduces brighter `+` and `*` particle detail.
- A transient produces a brief deterministic outward burst of `-` and `=` streaks on the reactive plane. The streaks are absent on the next non-transient frame.
- Lost or stale audio continues through the existing signal-settling behavior, leaving a quiet ambient field rather than an empty or frozen center.

No random generator, mutable particle simulation, particle objects, new dependency, scene registry, or configuration option is required.

## Acceptance criteria

1. The left and right architecture borders retain dense, full-height coverage at established wide and portrait render sizes.
2. Architecture between the bulkheads is nearly empty and contains no portal edge, catwalk, floor, horizon, or focal-axis construction.
3. The center particle field is nonempty, meaningfully occupied, non-solid, and has no long rigid horizontal edge.
4. Bass changes particle positions and cluster spread; midrange changes lateral shear; treble changes particle glyph and detail distribution; a transient changes only the short-lived reactive burst relative to a matching non-transient frame.
5. Matching width, height, bands, tick, and seed produce identical frames with identical dimensions.
6. Every rendered glyph is ASCII, and batgrl continues to present five persistent transparent truecolor text planes.
7. Lost or stale audio settles to the existing quiet signal state and leaves visible ambient particles.

## Verification evidence

Automated tests should measure side-border architecture density, center architecture sparsity, center particle occupancy, absence of long rigid particle rows, distinct frequency-band reactions, transient lifetime, fixed dimensions, determinism, and ASCII-only output. Representative calm, bass-heavy, mid-heavy, treble-heavy, and transient renders should also be inspected because exact ASCII aesthetics are not usefully snapshot-tested.
