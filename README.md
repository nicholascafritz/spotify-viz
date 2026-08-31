# spotify-viz

A real-time, liminal ASCII visualizer for `ncspot`. It listens to the active PipeWire/PulseAudio output monitor through CAVA and displays ncspot metadata through MPRIS.

## Install

```sh
sudo apt install cava playerctl
uv tool install --editable /home/user/spotify-viz
```

## Run

Start music in `spotify`, then open another terminal:

```sh
spotify-viz
```

If automatic output-monitor discovery selects the wrong source:

```sh
spotify-viz --source alsa_output.pci-0000_00_1b.0.analog-stereo.monitor
```

## Controls

- `q`: quit (ncspot keeps playing)
- `Space`: pause/resume ncspot only
- `h`: display scene key help
- `m`: reserved for additional scenes

The corridor is audio-reactive: bass bends the structure, mids place debris, and treble raises scanline detail. The display uses Kitty truecolor but remains usable in ordinary ANSI terminals.

## Development

```sh
uv run --with pytest pytest -v
uv run spotify-viz
```
