from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from .utils import tags



@dataclass
class SubtitleStream:
    index: int
    # subrip, ass, hdmv_pgs_subtitle, dvd_subtitle...
    codec: str
    language: str | None = None
    title: str | None = None
    default: bool = False
    forced: bool = False
    hearing_impaired: bool = False

    @classmethod
    def from_ffprobe(cls, raw: dict[str, Any]) -> "SubtitleStream":
        sub_tags = tags(raw)
        disp: dict[str, str] = raw.get("disposition", {})

        return cls(
            index=raw["index"],
            codec=raw.get("codec_name", "unknown"),
            language=sub_tags.get("language"),
            title=sub_tags.get("title"),
            default=bool(disp.get("default")),
            forced=bool(disp.get("forced")),
            hearing_impaired=bool(disp.get("hearing_impaired")),
        )



@dataclass
class SubtitleStreams:
    streams: list[SubtitleStream] = field(default_factory=list)
    copy: bool = True
    filepath: Path | None = None

    @property
    def nstreams(self) -> int:
        return len(self.streams)


TEXT_CODECS = {
    "subrip",
    "ass",
    "ssa",
    "webvtt",
    "mov_text"
}



def subtitle_codec_for(container: str, stream: SubtitleStream) -> str | None:
    if container == ".mkv":
        return "copy"

    if container == ".mp4":
        # PGS/VobSub impossible
        return "mov_text" if stream.codec in TEXT_CODECS else None

    return "copy"
