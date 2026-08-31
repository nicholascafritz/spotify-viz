# spotify-viz

`spotify-viz` is a standalone, full-screen ASCII visualizer for ncspot. It uses batgrl's retained-mode terminal renderer for stable truecolor layers, observes the active PipeWire/PulseAudio output monitor through CAVA, and uses MPRIS only for ncspot metadata and play/pause.

The scene is an impossible server cathedral: dense structural bays, catwalks, cable runs, atmosphere, and bounded scanline damage surround an off-centre violet void. Bass breathes the void and camera, midrange moves depth layers, treble adds cyan interference, and transients create brief signal tears. It uses only ASCII glyphs and fixed terminal cells.

Requirements

- Debian/Ubuntu runtime packages: `cava`, `playerctl`, PipeWire/PulseAudio compatibility
- A truecolor terminal (Kitty is the intended terminal; batgrl owns the alternate screen and resize lifecycle)
- ncspot signed into Spotify; Spotify Premium is required by ncspot, not by this project
- Python 3.13 and `uv` for development

Install dependencies

```sh
sudo apt install cava playerctl
uv sync
```

Run beside ncspot

```sh
spotify
uv run spotify-viz
```

For an installed command:

```sh
uv tool install --editable /home/user/spotify-viz
spotify-viz
```

The visualizer never embeds, restarts, or terminates ncspot. `Space` issues exactly `playerctl --player=ncspot play-pause`, so other MPRIS players are not controlled.

Configuration

The optional configuration file is:

```text
$XDG_CONFIG_HOME/spotify-viz/config.toml
# defaults to ~/.config/spotify-viz/config.toml
```

Supported keys:

```toml
scene = "corridor"
fps = 30                 # 1 through 60
motion_intensity = 0.65  # 0.0 through 1.0
show_status = true
audio_source = "alsa_output.pci-0000_00_1b.0.analog-stereo.monitor"

[palette]
structure = "#58ff9e"
reactive = "#50dcff"
warning = "#ffbe46"
error = "#ff5454"
```

Use an explicit config or monitor override when needed:

```sh
spotify-viz --config ~/.config/spotify-viz/config.toml
spotify-viz --source alsa_output.pci-0000_00_1b.0.analog-stereo.monitor
```

Without `audio_source`, the launcher queries `pactl get-default-sink` and subscribes to that sink's `.monitor` source. List available sources with:

```sh
pactl list short sources
```

Controls

- `q`: quit and restore the normal terminal; ncspot continues playing
- `Space`: toggle only ncspot playback
- `m`: cycle available scenes
- `h`: show or hide the compact key reference

Failure behavior

- `NO SIGNAL`: ncspot metadata is unavailable; the audio scene keeps running.
- `AUDIO STALE`: no recent CAVA data; the last scene settles rather than blocking.
- `AUDIO TAP LOST`: CAVA or the selected monitor exited/unavailable; a quiet scene remains visible.
- Small terminals use a compact horizon without a status line or horizontal scrolling.

Development and verification

```sh
uv run pytest -v
uv build
```

Live acceptance requires a real terminal, PipeWire monitor, and playing ncspot track. Start `spotify-viz`, resize it between wide and compact layouts, confirm its status line follows ncspot, test `Space` while another MPRIS player is active, then press `q` and verify ncspot remains playing.
