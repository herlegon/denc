from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from .media_stream import MediaStream
    from .subtitles import SubtitleStreams

from .subtitles import subtitle_codec_for
from .utils import tags
from .dlogger import dlogger



@dataclass
class AudioStream:
    index: int
    codec: str
    language: str | None = None
    title: str | None = None
    default: bool = False

    @classmethod
    def from_ffprobe(cls, raw: dict[str, Any]) -> "AudioStream":
        audio_tags = tags(raw)

        return cls(
            index=raw["index"],
            codec=raw.get("codec_name", "unknown"),
            language=audio_tags.get("language"),
            title=audio_tags.get("title"),
            default=bool(raw.get("disposition", {}).get("default")),
        )



@dataclass
class AudioStreams:
    streams: list[AudioStream] = field(default_factory=list)
    copy: bool = True
    filepath: Path | None = None

    @property
    def nstreams(self) -> int:
        return len(self.streams)



class AudioCodec(Enum):
    AAC = "aac"
    MP3 = "libmp3lame"
    OPUS = "libopus"



acodec_to_ffmpeg_acodec: dict[AudioCodec, str] = {
    AudioCodec.AAC: "aac",
    AudioCodec.MP3: "libmp3lame",
    AudioCodec.OPUS: "libopus",
}




def audio_subtitles_copy_args(media: MediaStream) -> tuple[list[str], list[str]]:
    container = media.filepath.suffix.lower()
    default_file = media.video.filepath
    files: list[str] = []
    args: list[str] = []
    out_count = {"a": 0, "s": 0}

    def input_index(path: Path) -> int:
        p = str(Path(path).resolve())
        if p not in files:
            files.append(p)
        # video input is 0
        return files.index(p) + 1

    def add_stream(
        group: AudioStreams | SubtitleStreams,
        stream,
        kind: str,
        codec: str
    ) -> None:
        idx = input_index(group.filepath or default_file)
        n = out_count[kind]
        args.extend(["-map", f"{idx}:{stream.index}", f"-c:{kind}:{n}", codec])
        out_count[kind] += 1

    def add_streams(group: AudioStreams | SubtitleStreams, kind: str, codec_for) -> None:
        if not group.copy:
            return
        for stream in group.streams:
            codec = codec_for(stream)
            if codec is None:
                dlogger.warning(
                    "Stream %s (%s) ignoré : incompatible avec %s",
                    stream.index, stream.codec, container,
                )
                continue
            add_stream(group, stream, kind, codec)

    add_streams(media.audio, "a", lambda s: "copy")
    add_streams(media.subtitles, "s", lambda s: subtitle_codec_for(container, s))

    extra_inputs = [arg for p in files for arg in ("-i", p)]
    return extra_inputs, args
