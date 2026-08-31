# spotify-viz design

## Purpose

`spotify-viz` is a standalone, audio-reactive terminal visualizer for the existing ncspot Spotify player. It should look like a living 1990s hacker-appliance display: an unsettling liminal ASCII space, not a conventional equalizer with decoration.

The visualizer launches independently beside ncspot. It follows system audio from PipeWire and uses ncspot only for now-playing metadata and play/pause control.

## Confirmed environment

- Host: Debian Trixie, x86_64
- Terminal: Kitty (`TERM=xterm-kitty`) with truecolor support
- Audio: PipeWire, PipeWire-Pulse, and WirePlumber are active
- Active system-audio monitor: `alsa_output.pci-0000_00_1b.0.analog-stereo.monitor`
- Player: Flatpak ncspot 1.3.4, exposed through MPRIS as `ncspot.instance2`
- Metadata/control bridge: `playerctl --player=ncspot`
- Existing launcher: `spotify` runs ncspot

## User interface

### Launch

`spotify-viz` opens its own alternate-screen terminal interface. It never embeds into, replaces, or restarts ncspot.

### Scene

The main canvas is an ASCII liminal space with three visual planes:

1. Structural plane: a receding corridor/grid with impossible doorways, perspective bends, and a distant void.
2. Atmospheric plane: drifting glyph debris, scanline fragments, and sparse spatial artifacts.
3. Reactive plane: an audio horizon and transient effects that react to frequency bands.

No dashboard panels, boxed widgets, startup inventory, or decorative rainbow animation are permitted.

### Palette

- Background: gunmetal-black
- Structural geometry: phosphor green
- Peaks, motion edges, and the audio horizon: cyan
- Warnings: amber
- Errors: red

Color represents state; it must not cycle decoratively.

### Audio-to-motion mapping

- Bass controls perspective compression, corridor curvature, doorway opening, and large spatial displacement.
- Midrange controls debris density, lateral motion, and doorway drift.
- Treble controls scanline breakup, glyph sparks, and fine spatial noise.
- Beat transients trigger short positional jumps. The scene must settle immediately after a transient rather than becoming continuously chaotic.

### Status readout

A thin, fixed bottom readout presents artist, title, playback state, elapsed time, and audio source state. It is hidden in compact layout mode.

### Controls

| Key | Action |
| --- | --- |
| `q` | Quit and restore terminal state |
| `Space` | Toggle ncspot playback through MPRIS |
| `m` | Cycle the available liminal scenes |
| `h` | Show or dismiss a compact key reference |

Terminal resizes reflow the canvas without restarting the process.

## Architecture

```
spotify-viz launcher
    |
    +-- CAVA spectrum bridge
    |       PipeWire output monitor -> frequency bands
    |
    +-- MPRIS bridge
    |       playerctl --player=ncspot -> metadata and playback control
    |
    +-- renderer
            alternate screen, frame clock, scene state, layout, input
```

### CAVA spectrum bridge

CAVA is responsible for real-time FFT analysis of the PipeWire output-monitor source. It publishes normalized frequency-band data to the renderer through a local stream. The renderer must not own PipeWire device capture or reimplement FFT analysis.

### MPRIS bridge

The metadata bridge polls ncspot’s MPRIS identity at a low cadence and normalizes artist, title, status, and position. Player controls are scoped to `ncspot` so Chromium or other MPRIS players cannot be controlled accidentally.

### Renderer

The renderer owns the alternate screen and cursor visibility, a fixed-rate frame scheduler, input handling, terminal-size layout selection, color composition, and deterministic scene state. Blocking CAVA and MPRIS reads must run outside the render path. Rendering must remain responsive if either source is stale.

### Configuration

User configuration is a TOML file with:

- default scene
- FPS cap
- palette overrides
- motion intensity
- status-readout visibility
- optional explicit PipeWire monitor source

The default audio source is the active system output monitor discovered from PipeWire/PulseAudio. An explicit configured source takes precedence.

## Layout behavior

- Wide layout: full liminal canvas with bottom readout.
- Compact layout: a restrained audio horizon and status-only presentation; no clipped art or horizontal scrolling.
- The renderer measures printable cell width, not ANSI escape length.
- All frames have stable dimensions for a given terminal size; no layout jump from metadata length or visual effects.

## Failure behavior

| Condition | Behavior |
| --- | --- |
| ncspot/MPRIS unavailable | Keep audio visualization running; display `NO SIGNAL` in the status line |
| PipeWire monitor or CAVA stream unavailable | Hold a quiet low-noise scene and display `AUDIO TAP LOST` |
| Metadata temporarily unavailable | Retain the last known track text with stale state; do not clear/flicker |
| Small terminal | Use compact layout |
| Renderer failure/exit | Restore cursor and terminal screen; terminate only visualizer-owned subprocesses |

## Dependencies and packaging

- Runtime dependencies: `cava`, `playerctl`, PipeWire/PulseAudio compatibility, and a truecolor terminal.
- Implementation language and package layout are deferred to the implementation plan.
- The repository must not include Spotify credentials, PipeWire device secrets, or user-specific runtime state.

## Verification requirements

1. Unit-test frequency-band normalization, audio-to-motion mapping, frame timing, layout selection, palette/state transitions, and terminal-size behavior.
2. Exercise renderer input and cleanup behavior without live Spotify credentials using fake spectrum and MPRIS sources.
3. Run live with the active PipeWire monitor while ncspot plays audio; verify scene movement responds to bass, mids, treble, and transients.
4. Confirm the bottom readout follows ncspot metadata and `Space` controls only ncspot.
5. Resize during playback and verify no artifacting, clipping, or process restart.
6. Quit during playback and verify normal terminal state returns and ncspot continues playing.

## Repository

Local repository: `/home/user/spotify-viz`

Branch: `main`

A remote GitHub repository is intentionally not created until its owner and visibility are explicitly chosen.
