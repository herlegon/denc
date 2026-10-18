from __future__ import annotations

import re
from typing import TYPE_CHECKING

from hytils import red
from .time_conversions import (
    frame_to_sexagesimal,
    sexagesimal_to_frame,
    frame_to_s,
)

if TYPE_CHECKING:
    from .vstream import VideoStream

_FRAME_RE = re.compile(r"^(\d+)f$")


def _unset(value: int | str | None) -> bool:
    """Return True for None, '' or a negative int (legacy -1 sentinel)."""
    return value is None or value == "" or (isinstance(value, int) and value < 0)


class Seek:
    """Frame range [start, to) of a video. `to` is exclusive.

    Each value can be an int (frame number), a "123f" string, or a
    sexagesimal time such as "00:01:30.5".
    `count` takes priority over `to` when both are given.
    With neither `count` nor `to`, the range extends to the end of the video.
    """

    def __init__(
        self,
        vstream: VideoStream,
        start: int | str | None = 0,
        count: int | str | None = None,
        to: int | str | None = None,
    ) -> None:
        if not vstream.is_frame_rate_fixed:
            raise NotImplementedError("[E] variable frame rate is not supported yet")
        self.vstream = vstream
        self._start: int = 0
        self._count: int | None = None  # None = up to the end of the video

        if not _unset(start):
            self.start = start
        # `count` has priority over `to`
        if not _unset(count):
            self.count = count
        elif not _unset(to):
            self.to = to

    # ---- conversion ----
    def _to_frames(self, value: int | str, name: str) -> int:
        """Convert an int, "123f" or sexagesimal value to a frame number."""
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError(red(f"Invalid {name} value: {value!r}"))
        if isinstance(value, int):
            frames = value
        else:
            value = value.strip()
            if not value:
                raise ValueError(red(f"Invalid {name} value: {value!r}"))
            if m := _FRAME_RE.match(value):
                frames = int(m.group(1))
            else:
                frames = sexagesimal_to_frame(value, self.vstream.frame_rate_r)
        if frames < 0:
            raise ValueError(red(f"Negative {name} value: {frames}"))
        return frames

    # ---- start ----
    @property
    def start(self) -> int:
        """First frame of the range (0-based)."""
        return self._start

    @start.setter
    def start(self, value: int | str) -> None:
        frames = self._to_frames(value, "start")
        if frames >= self.vstream.frame_count:
            raise ValueError(
                red(f"Erroneous start value: {frames} >= {self.vstream.frame_count}")
            )
        self._start = frames

    @property
    def start_hms(self) -> str:
        """Start as a sexagesimal time, or '' if start == 0 (no -ss needed)."""
        if self.start > 0:
            return frame_to_sexagesimal(self.start, self.vstream.frame_rate_r)
        return ""

    # ---- count ----
    @property
    def count(self) -> int:
        """Number of frames in the range, clamped to the end of the video."""
        remaining = self.vstream.frame_count - self._start
        return remaining if self._count is None else min(self._count, remaining)

    @count.setter
    def count(self, value: int | str) -> None:
        frames = self._to_frames(value, "count")
        if frames == 0:
            raise ValueError(red("Erroneous count value: 0"))
        self._count = frames

    @property
    def duration(self) -> str:
        """Duration in seconds (for -t), or '' if the range runs to the end."""
        if self._count is None:
            return ""
        return f"{frame_to_s(self.count, self.vstream.frame_rate_r)}"

    # ---- to (exclusive) ----
    @property
    def to(self) -> int:
        """End frame (exclusive), derived from start and count."""
        return self._start + self.count

    @to.setter
    def to(self, value: int | str) -> None:
        frames = self._to_frames(value, "to")
        if frames <= self._start:
            raise ValueError(red(f"Erroneous end value: {frames} <= {self._start}"))
        # Clamped to frame_count in the `count` getter
        self._count = frames - self._start

    @property
    def to_hms(self) -> str:
        """End as a sexagesimal time, or '' if the range runs to the end."""
        if self._count is None:
            return ""
        return frame_to_sexagesimal(self.to, self.vstream.frame_rate_r)

    # ---- FFmpeg ----
    @property
    def input_args(self) -> list[str]:
        """Options to place BEFORE the relevant -i."""
        args: list[str] = []
        if self.start > 0:
            args += ["-ss", self.start_hms]
        if self._count is not None:
            args += ["-t", self.duration]
        return args

    def __str__(self) -> str:
        return (
            f"Seek(start={self.start} [{self.start_hms or '0'}], "
            f"count={self.count}, to={self.to}, "
            f"frame_count={self.vstream.frame_count})"
        )
