from __future__ import annotations
from copy import copy, deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from .encoder import write
from .seek import Seek
from .vstream import OutVideoStream, VideoStream



@dataclass
class AudioInfo:
    nstreams: int = 0



@dataclass
class SubtitleInfo:
    nstreams: int = 0



@dataclass
class MediaStream:
    video: VideoStream | OutVideoStream
    audio: AudioInfo | None = None
    subtitles: SubtitleInfo | None = None
    seek: Seek = field(default=None, init=False)
    filepath: Optional[Path] = None
    # Add the property to the basename
    add_prop_suffix: bool = False

    def __post_init__(self) -> None:
        if self.video is not None:
            self.video.parent = self

        if isinstance(self.video, OutVideoStream):
            self.video.filepath = self.filepath
            self.video.add_prop_suffix = self.add_prop_suffix

        self.seek = Seek(vstream=self.video)


    def set_seek(self, start: int = -1, count: int = -1, end: int = -1) -> None:
        def _is_set(arg) -> bool:
            if (
                (isinstance(arg, int) and arg >= 0)
                or (isinstance(arg, str) and arg)
            ):
                return True
            return False

        if _is_set(start):
            self.seek.start = start

        if _is_set(count):
            self.seek.count = count

        if _is_set(end):
            self.seek.to = end


    def write(self, frames):
        return write(self, frames)


    def copy(self) -> "MediaStream":
        new_video = (
            None if self.video is None
            else OutVideoStream.from_video_stream(self.video)
        )
        return replace(
            self,
            video=new_video,
            audio=deepcopy(self.audio),
            subtitles=deepcopy(self.subtitles),
        )
