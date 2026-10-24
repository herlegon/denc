from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Optional

from .encoder import write
from .seek import Seek
from .vstream import OutVideoStream, VideoStream

from .audio import AudioStreams
from .subtitles import SubtitleStreams
from .container import ContainerFormat


@dataclass
class MediaStream:
    video: VideoStream | OutVideoStream
    audio: AudioStreams | None = None
    subtitles: SubtitleStreams | None = None
    seek: Seek = field(default=None, init=False)
    filepath: Optional[Path] = None
    container: Optional[ContainerFormat] = field(default=None, init=False)
    overwrite: bool = False,
    # Add the property to the basename
    add_prop_suffix: bool = False


    def __post_init__(self) -> None:
        if self.filepath is not None:
            self.container = self.filepath.suffix

        if self.video is not None:
            self.video.parent = self

        if isinstance(self.video, OutVideoStream):
            self.video.filepath = self.filepath
            self.video.add_prop_suffix = self.add_prop_suffix

        # Seek is also copied if video is output: for statitiscs (progression)
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


    def to_output(self, filepath: Path | None = None) -> "MediaStream":
        """Génère le MediaStream de sortie, prêt à être configuré
        (filepath, codec, crf, preset...) puis utilisé pour construire
        la commande FFmpeg.

        Reprend de la source : shape, frame rate, pix_fmt, sar/dar, color, etc.
        Réinitialise : seek (nouveau Seek) et filepath.
        """
        if self.video is None:
            raise ValueError("to_output() requires a video stream")

        audio: AudioStreams = deepcopy(self.audio)
        audio.filepath = self.filepath

        subtitles: SubtitleStreams = deepcopy(self.subtitles)
        subtitles.filepath = self.filepath

        return replace(
            self,
            video=OutVideoStream.from_video_stream(self.video),
            audio=audio,
            subtitles=subtitles,
            filepath=filepath,
            # seek est recréé par __post_init__
        )

