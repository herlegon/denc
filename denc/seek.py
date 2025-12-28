
from __future__ import annotations
from dataclasses import dataclass
from hytils import red
import re
from typing import TYPE_CHECKING, Optional

from .utils.time_conversions import (
    FrameRate,
    frame_to_sexagesimal,
    sexagesimal_to_frame,
    frame_to_s
)
if TYPE_CHECKING:
    from .vstream import VideoStream



@dataclass
class Seek:
    vstream: VideoStream
    _start: Optional[int] = -1
    _count: Optional[int] = -1
    _to: Optional[int] = -1

    @property
    def start(self) -> int:
        if self._start is None or self._start < 0:
            if (
                self._to is not None and self._to > 0
                and self._count is not None and self._count > 0
            ):
                return self._to - self._count
            return 0
        return self._start


    @property
    def start_hms(self) -> str:
        if self.start > 0:
            return frame_to_sexagesimal(self.start, self.vstream.frame_rate_r)
        return ""


    @start.setter
    def start(self, value: int | str) -> None:
        _start: int = 0
        if isinstance(value, int):
            _start = value
        elif isinstance(value, str) and value:
            # Convert from str to frame no.
            if result := re.search(re.compile(r"^(\d+)f$"), value):
                _start = int(result.group(1))
            else:
                _start = sexagesimal_to_frame(value, self.vstream.frame_rate_r)
        else:
            raise ValueError(f"Invalid start value: {value!r}")

        if _start >= self.vstream.frame_count:
            raise ValueError(
                red(f"Erroneous start value: {self.start} > {self.vstream.frame_count}")
            )

        self._start = _start


    @property
    def count(self) -> int:
        _start: int = 0 if self._start is None or self._start < 0 else self._start
        _count: int = 0 if self._count is None else self._count
        return min(self.vstream.frame_count - _start, _count)


    @property
    def duration(self) -> int | str:
        _start: int = 0 if self._start is None or self._start < 0 else self._start
        _count: int = 0 if self._count is None or self._count < 0 else self._count
        _to: int = 0 if self._to is None  or self._to < 0 else self._to

        if _count <= 0:
            if _start > 0 and _to > _start:
                return min(_to - _start, self.vstream.frame_count - _start)
            return ""
        return f"{frame_to_s(self.count, self.vstream.frame_rate_r)}"


    @count.setter
    def count(self, value: int | str) -> None:
        _value: int = 0
        if isinstance(value, int):
            _value = value
        elif isinstance(value, str) and value:
            # Convert from str to frame no.
            if result := re.search(re.compile(r"^(\d+)f$"), value):
                _value = int(result.group(1))
            else:
                _value = sexagesimal_to_frame(value, self.vstream.frame_rate_r)
        self._count = _value
        self._to = -1


    @property
    def to(self) -> int:
        _start: int = 0 if self._start is None or self._start < 0 else self._start
        _count: int = 0 if self._count is None or self._count < 0 else self._count
        _to: int = 0 if self._to is None  or self._to < 0 else self._to
        if _to <= _start or _to > _start + _count:
            raise ValueError(red(f"Erroneous end value: {_to} < {_start}"))
        return _to


    @property
    def to_hms(self) -> str:
        if self._to is None or self._to <= 0:
            return "0.000"
        return frame_to_sexagesimal(self._to, self.vstream.frame_rate_r)


    @to.setter
    def to(self, value: int | str) -> None:
        _value: int = 0
        if isinstance(value, int):
            _value = value
        elif isinstance(value, str) and value:
            # Convert from str to frame no.
            if result := re.search(re.compile(r"^(\d+)f$"), value):
                _value = int(result.group(1))
            else:
                _value = sexagesimal_to_frame(value, self.vstream.frame_rate_r)

        _start: int = 0 if self._start is None or self._start < 0 else self._start
        if _value <= _start:
            raise ValueError(red(f"Erroneous end value: {value} < {self._start}"))
        self._to = _value

        _to: int = 0 if self._to is None or self._to < 0 else self._to
        if _start > 0:
            self._count = _to - _start
        else:
            self._count = _to


    def __str__(self):
        string: str = f"""Seek(
    _start={self._start},
    start_hms={self.start_hms},
    _count={self._count},
    _to={self._to},

    duration={self.duration},
    vstream.framecount={self.vstream.frame_count}

    start={self.start},
    count={self.count},
)"""
        return string




    def _consolidate(
        self,
        vstream: VideoStream,
        start: int | str = 0,
        duration: int | str = -1,
        end: int | str = -1,
    ) -> Seek:
        # vstream: VideoStream = stream.video

        if not vstream.is_frame_rate_fixed:
            raise NotImplementedError("[E] variable frame rate is not supported yet")

        frame_rate: FrameRate = vstream.frame_rate_r


        # Start
        start_no: int = 0
        if isinstance(start, int):
            start_no = start
        elif isinstance(start, str) and start:
            # Convert from str to frame no.
            if result := re.search(re.compile(r"^(\d+)f$"), start):
                start_no = int(result.group(1))
            else:
                start_no = sexagesimal_to_frame(start, frame_rate)

        if start_no >= vstream.frame_count:
            raise ValueError(red(f"Erroneous seek start: {start} >= {vstream.frame_count}"))
        print(yellow(f"start:"))
        # Duration
        count: int = -1
        if isinstance(duration, int):
            count = duration
        elif isinstance(duration, str) and duration:
            if result := re.search(re.compile(r"^(\d+)f$"), duration):
                count = int(result.group(1))
            else:
                count = sexagesimal_to_frame(duration, frame_rate)
        count = min(count, vstream.frame_count)

        # End
        end_no: int = -1
        if isinstance(end, int):
            end_no = end
        elif isinstance(end, str) and end:
            if result := re.search(re.compile(r"^(\d+)f$"), end):
                end_no = int(result.group(1))
            else:
                end_no = sexagesimal_to_frame(end, frame_rate)
        count = min(end_no, vstream.frame_count)

        max_count = vstream.frame_count
        if start_no > 0:
            if end_no >= start_no:
                raise ValueError(red(f"Erroneous seek end: {end} > {start}"))
            max_count = end_no - start_no

        # Only start is specified
        if count <= 0 and end_no <= 0:
            count = max_count - start_no
        # count is specified and has the priority
        elif count > 0:
            end_no = start_no + count
        # end is specified: low priority
        elif end_no > 0:
            if end_no < start_no:
                raise ValueError(red(f"Erroneous seek end: {end} < {start}"))
            count = end_no - start_no

        return Seek(
            vstream=vstream,
            start=start_no,
            start_hms=frame_to_sexagesimal(start_no, frame_rate),
            count=count,
            duration=frame_to_sexagesimal(count, frame_rate) if count else "",
            to=end_no,
            to_hms=frame_to_sexagesimal(end_no, frame_rate) if end_no else "",
        )
