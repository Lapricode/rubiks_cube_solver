"""Offscreen pygame panels displayed inside Tkinter widgets."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass

import pygame
from PIL import Image, ImageTk

Color = str | tuple[int, int, int]
SoundPlayer = Callable[[str, str], None]
RedrawCallback = Callable[[], None]


@dataclass
class HitRegion:
    key: str
    rect: pygame.Rect
    callback: Callable[[], None]
    cursor: str = "hand2"
    position_callback: Callable[[float], None] | None = None


class PygamePanel:
    """Render a pygame surface and show it in a Tkinter label."""

    def __init__(
        self,
        master: tk.Misc,
        width: float,
        height: float,
        background: Color,
        sound_player: SoundPlayer | None = None,
    ) -> None:
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.background = background
        self.surface = pygame.Surface((self.width, self.height))
        self.frame = tk.Frame(master, bg=background, bd=0, highlightthickness=0)
        self.label = tk.Label(self.frame, bd=0, highlightthickness=0, bg=background)
        self.label.pack(fill=tk.BOTH, expand=True)
        self.label.configure(anchor="nw")
        self.on_redraw: RedrawCallback | None = None
        self.sound_player = sound_player
        self.regions: list[HitRegion] = []
        self.hovered_key: str | None = None
        self._drag_region: HitRegion | None = None
        self._photo: ImageTk.PhotoImage | None = None
        self._font_cache: dict[tuple[int, bool, bool, bool], pygame.font.Font] = {}
        self.label.bind("<Button-1>", self._on_click)
        self.label.bind("<B1-Motion>", self._on_drag)
        self.label.bind("<ButtonRelease-1>", self._on_release)
        self.label.bind("<Motion>", self._on_motion)
        self.label.bind("<Leave>", self._on_leave)

    def resize(self, width: float, height: float) -> bool:
        new_width = max(1, int(width))
        new_height = max(1, int(height))
        if (new_width, new_height) == (self.width, self.height):
            return False
        self.width = new_width
        self.height = new_height
        self.surface = pygame.Surface((self.width, self.height))
        self.hovered_key = None
        self._drag_region = None
        return True

    def begin(self, background: Color | None = None) -> None:
        self.surface.fill(background if background is not None else self.background)
        self.regions = []

    def finish(self) -> None:
        image = Image.frombytes(
            "RGB",
            (self.width, self.height),
            pygame.image.tobytes(self.surface, "RGB"),
        )
        self._photo = ImageTk.PhotoImage(image)
        self.label.configure(image=self._photo)

    def redraw(self) -> None:
        if self.on_redraw is not None:
            self.on_redraw()

    def font(
        self, size: int, bold: bool = False, italic: bool = False, serif: bool = False
    ) -> pygame.font.Font:
        key = (max(7, int(size)), bold, italic, serif)
        if key not in self._font_cache:
            family = "dejavuserif" if serif else "dejavusans"
            self._font_cache[key] = pygame.font.SysFont(family, key[0], bold=bold, italic=italic)
        return self._font_cache[key]

    def text(
        self,
        text: str,
        x: float,
        y: float,
        size: int = 12,
        color: Color = (0, 0, 0),
        anchor: str = "nw",
        bold: bool = False,
        italic: bool = False,
        serif: bool = False,
        max_width: float | None = None,
        max_lines: int | None = None,
        line_height: float | None = None,
    ) -> float:
        font = self.font(size, bold, italic, serif)
        lines = self._wrap(text, font, max_width) if max_width is not None else text.splitlines()
        if not lines:
            lines = [""]
        if max_lines is not None and len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = self._ellipsize(lines[-1], font, max_width)
        line_height = line_height or font.get_linesize()
        total_height = line_height * len(lines)
        draw_x = x
        if anchor in ("center", "w", "e"):
            draw_y = y - total_height / 2
        elif anchor in ("sw", "s", "se"):
            draw_y = y - total_height
        else:
            draw_y = y
        for index, line in enumerate(lines):
            image = font.render(line, True, color)
            if anchor in ("center", "n", "s"):
                item_x = draw_x - image.get_width() / 2
            elif anchor in ("ne", "e", "se"):
                item_x = draw_x - image.get_width()
            else:
                item_x = draw_x
            self.surface.blit(image, (round(item_x), round(draw_y + index * line_height)))
        return total_height

    def rect(
        self,
        rect: pygame.Rect | tuple[float, float, float, float],
        color: Color,
        width: int = 0,
        border_radius: int = 0,
    ) -> None:
        pygame.draw.rect(
            self.surface,
            color,
            pygame.Rect(round(rect[0]), round(rect[1]), round(rect[2]), round(rect[3])),
            width=width,
            border_radius=border_radius,
        )

    def line(self, start: tuple[float, float], end: tuple[float, float], color: Color) -> None:
        pygame.draw.line(self.surface, color, start, end, 1)

    def circle(
        self,
        center: tuple[float, float],
        radius: float,
        color: Color,
        width: int = 0,
    ) -> None:
        pygame.draw.circle(
            self.surface,
            color,
            (round(center[0]), round(center[1])),
            round(radius),
            width=width,
        )

    def button(
        self,
        key: str,
        rect: pygame.Rect | tuple[float, float, float, float],
        text: str,
        size: int,
        fg: Color,
        bg: Color,
        callback: Callable[[], None],
        hover_bg: Color | None = None,
        outline: Color | None = None,
        border_radius: int = 4,
    ) -> None:
        button_rect = pygame.Rect(round(rect[0]), round(rect[1]), round(rect[2]), round(rect[3]))
        fill = hover_bg if key == self.hovered_key and hover_bg is not None else bg
        self.rect(button_rect, fill, border_radius=border_radius)
        if outline is not None:
            self.rect(button_rect, outline, width=1, border_radius=border_radius)
        self.text(
            text,
            button_rect.centerx,
            button_rect.centery,
            size=size,
            color=fg,
            anchor="center",
            bold=True,
            max_width=max(10, button_rect.width - 10),
            max_lines=2,
            line_height=max(10, size + 2),
        )
        self.regions.append(HitRegion(key, button_rect, callback))

    def slider(
        self,
        key: str,
        rect: pygame.Rect | tuple[float, float, float, float],
        value: float,
        callback: Callable[[float], None],
        track_color: Color,
        fill_color: Color,
        knob_color: Color,
        outline: Color | None = None,
    ) -> None:
        slider_rect = pygame.Rect(round(rect[0]), round(rect[1]), round(rect[2]), round(rect[3]))
        fraction = min(1.0, max(0.0, value))
        track_height = max(4, slider_rect.height // 4)
        track = pygame.Rect(
            slider_rect.left + 4,
            slider_rect.centery - track_height // 2,
            max(8, slider_rect.width - 8),
            track_height,
        )
        self.rect(track, track_color, border_radius=track_height // 2)
        filled = track.copy()
        filled.width = max(1, round(track.width * fraction))
        self.rect(filled, fill_color, border_radius=track_height // 2)
        knob_x = track.left + round(track.width * fraction)
        knob_radius = max(5, slider_rect.height // 2 - 2)
        self.circle((knob_x, track.centery), knob_radius, knob_color)
        if outline is not None:
            self.circle((knob_x, track.centery), knob_radius, outline, width=1)
        self.regions.append(
            HitRegion(
                key,
                slider_rect,
                lambda: None,
                cursor="hand2",
                position_callback=lambda position: callback(min(1.0, max(0.0, position))),
            )
        )

    def link(
        self,
        key: str,
        rect: pygame.Rect | tuple[float, float, float, float],
        text: str,
        size: int,
        color: Color,
        callback: Callable[[], None],
        hover_color: Color | None = None,
    ) -> None:
        link_rect = pygame.Rect(round(rect[0]), round(rect[1]), round(rect[2]), round(rect[3]))
        draw_color = hover_color if key == self.hovered_key and hover_color else color
        self.text(
            text,
            link_rect.centerx,
            link_rect.centery,
            size=size,
            color=draw_color,
            anchor="center",
            bold=True,
            max_width=max(10, link_rect.width - 6),
            max_lines=2,
        )
        self.regions.append(HitRegion(key, link_rect, callback))

    def _wrap(self, text: str, font: pygame.font.Font, max_width: float) -> list[str]:
        lines: list[str] = []
        for paragraph in text.splitlines() or [""]:
            if not paragraph:
                lines.append("")
                continue
            words = paragraph.split(" ")
            current = words[0]
            for word in words[1:]:
                candidate = f"{current} {word}"
                if font.size(candidate)[0] <= max_width:
                    current = candidate
                else:
                    lines.append(current)
                    current = word
            lines.append(current)
        return lines

    def _ellipsize(self, text: str, font: pygame.font.Font, max_width: float | None) -> str:
        if max_width is None:
            return text + "..."
        candidate = text
        while candidate and font.size(candidate + "...")[0] > max_width:
            candidate = candidate[:-1].rstrip()
        return candidate + "..." if candidate != text else text

    def _find_region(self, x: int, y: int) -> HitRegion | None:
        for region in reversed(self.regions):
            if region.rect.collidepoint(x, y):
                return region
        return None

    def _on_click(self, event: tk.Event) -> None:
        region = self._find_region(event.x, event.y)
        if region is None:
            return
        if self.sound_player is not None:
            self.sound_player("select_button_sound", "sound")
        if region.position_callback is not None:
            self._drag_region = region
            fraction = (event.x - region.rect.left) / max(1, region.rect.width)
            region.position_callback(fraction)
        else:
            region.callback()

    def _on_drag(self, event: tk.Event) -> None:
        region = self._drag_region
        if region is None or region.position_callback is None:
            return
        fraction = (event.x - region.rect.left) / max(1, region.rect.width)
        region.position_callback(min(1.0, max(0.0, fraction)))

    def _on_release(self, event: tk.Event) -> None:
        region = self._drag_region
        self._drag_region = None
        if region is None or region.position_callback is None:
            return
        fraction = (event.x - region.rect.left) / max(1, region.rect.width)
        region.position_callback(min(1.0, max(0.0, fraction)))
        self._on_motion(event)

    def _on_motion(self, event: tk.Event) -> None:
        region = self._find_region(event.x, event.y)
        key = region.key if region is not None else None
        self.label.configure(cursor=region.cursor if region is not None else "")
        if key == self.hovered_key:
            return
        self.hovered_key = key
        if key is not None and self.sound_player is not None:
            self.sound_player("hover_button_sound", "sound")
        self.redraw()

    def _on_leave(self, event: tk.Event) -> None:
        self.label.configure(cursor="")
        if self.hovered_key is None:
            return
        self.hovered_key = None
        self.redraw()
