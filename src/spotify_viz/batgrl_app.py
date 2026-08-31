from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from batgrl.app import App
from batgrl.colors import Color
from batgrl.gadgets.gadget import Gadget
from batgrl.gadgets.text import Text
from batgrl.terminal.events import KeyEvent

from .app import VisualizerApp, frame_delay
from .batgrl_renderer import BatgrlLayerStack, DenseCathedralComposer, LayeredFrame
from .config import VizConfig
from .terminal import ANSI_PATTERN

if TYPE_CHECKING:
    from .app import AudioSource, MetadataSource


STATUS_COLOR = Color(92, 229, 255)
STATUS_BG = Color(5, 12, 20)


class _DiscardingTerminal:
    def draw(self, content: str) -> None:
        del content


class _KeyInput(Gadget):
    def __init__(self, owner: BatgrlVisualizerApp) -> None:
        super().__init__(size=(1, 1), is_transparent=True)
        self.owner = owner

    def on_key(self, key_event: KeyEvent) -> bool:
        if key_event.ctrl and key_event.key == "c":
            self.owner.exit()
            return True
        if not self.owner.controller.handle_key(key_event.key.encode()):
            self.owner.exit()
        return True


class BatgrlVisualizerApp(App):
    """batgrl event loop and presentation layer over the existing bridges."""

    def __init__(self, *, config: VizConfig, cava: AudioSource, mpris: MetadataSource) -> None:
        super().__init__()
        self.config = config
        self._dimensions = (100, 30)
        self.controller = VisualizerApp(
            config=config,
            cava=cava,
            mpris=mpris,
            terminal=_DiscardingTerminal(),
            size_provider=lambda: self._dimensions,
        )
        self.composer = DenseCathedralComposer(seed=42)
        self.layers: BatgrlLayerStack | None = None
        self.status: Text | None = None
        self._input: _KeyInput | None = None
        self._closed = False

    def compose_once(self, *, columns: int, rows: int, now: float) -> LayeredFrame:
        self._dimensions = (max(1, columns), max(1, rows))
        layout = self.controller.advance(now=now)
        frame = self.composer.render(
            width=layout.canvas_width,
            height=layout.canvas_height,
            bands=self.controller.state.bands,
            tick=self.controller.state.tick,
        )
        self.controller.state.tick += 1
        return frame

    async def on_start(self) -> None:
        assert self.root is not None
        height, width = self.root.size
        self.layers = BatgrlLayerStack(size=(height, width))
        self.status = Text(size=(1, width), is_transparent=False)
        self._input = _KeyInput(self)
        self.add_gadget(self.layers)
        self.add_gadget(self.status)
        self.add_gadget(self._input)

        while True:
            started = time.monotonic()
            height, width = self.root.size
            frame = self.compose_once(columns=width, rows=height, now=started)
            self.layers.present(frame)
            self._input.size = (height, width)
            self._present_status(frame)
            await asyncio.sleep(frame_delay(fps=self.config.fps, started=started, now=time.monotonic()))

    def _present_status(self, frame: LayeredFrame) -> None:
        assert self.status is not None
        layout = self.controller.state.layout
        assert layout is not None
        self.status.is_visible = layout.status_visible
        if not layout.status_visible:
            return
        self.status.size = (1, frame.width)
        self.status.pos = (frame.height, 0)
        self.status.clear()
        line = ANSI_PATTERN.sub("", self.controller._status_line(frame.width))
        self.status.add_str(line, pos=(0, 0), fg_color=STATUS_COLOR, bg_color=STATUS_BG)

    def close(self) -> None:
        if not self._closed:
            self.controller.close()
            self._closed = True
