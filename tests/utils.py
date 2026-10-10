from enum import Enum
from pprint import pprint
import re
from dataclasses import dataclass, fields
from pathlib import Path
import signal
import sys

from hytils import lightcyan

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from denc import (
    VideoCodec,
    PixFmt,
    ColorSpace,
    VCODEC_PROFILES,
    VCODEC_TUNES,
    ColorRange,
    VCODECS_PRESETS,
    VCODEC_PROFILE_PIXFMT,
    OutVideoStream,
    vcodec_to_extension,
)
from denc.color_space import effective_color_range
from denc.crf import effective_crf
from denc.presets import effective_preset
from denc.profiles import effective_profile
from denc.tunes import effective_tune



_PRESET_TOKENS = {p.lower() for presets in VCODECS_PRESETS.values() for p in presets}  # use your actual table name
_TUNE_TOKENS = {t for tunes in VCODEC_TUNES.values() for t in tunes}


def _alternation(tokens) -> str:
    """Regex alternation, longest token first (h264_nvenc before h264)."""
    return "|".join(re.escape(t) for t in sorted(set(tokens), key=len, reverse=True))


# filename token -> enum member
_CODEC_BY_TOKEN: dict[str, VideoCodec] = {c.value.lower(): c for c in VideoCodec}
_PIXFMT_BY_TOKEN: dict[str, PixFmt] = {p.value.replace('le',''): p for p in PixFmt}
_MATRIX_BY_TOKEN: dict[str, ColorSpace] = {c.value: c for c in ColorSpace}  # BT709 is an alias of REC709


_TUNE_TOKENS = {t for tunes in VCODEC_TUNES.values() for t in tunes}
_PRESET_TOKENS = {p.lower() for presets in VCODECS_PRESETS.values() for p in presets}


_PROFILE_TOKENS = (
    {p for profile_pixfmts in VCODEC_PROFILE_PIXFMT.values() for p in profile_pixfmts}
    | {p for profiles in VCODEC_PROFILES.values() for p in profiles}
)
# filenames write DNxHR profiles without the prefix: dnxhr_lb_... -> `lb`
_PROFILE_TOKENS |= {p.removeprefix("dnxhr_") for p in VCODEC_PROFILES[VideoCodec.DNXHR]}








FILENAME_RE = re.compile(rf"""
    ^(?P<base>.+?)_
    (?P<width>\d+)x(?P<height>\d+)_
    (?P<codec>{_alternation(_CODEC_BY_TOKEN)})_
    (?:(?P<profile>{_alternation(_PROFILE_TOKENS)})_)?
    (?P<pix_fmt>{_alternation(_PIXFMT_BY_TOKEN)})_
    (?P<fps>\d+(?:\.\d+)?)fps
    (?:_(?P<matrix>{_alternation(_MATRIX_BY_TOKEN)}))?
    _(?P<color_range>{_alternation(r.value for r in ColorRange)})
    (?:_(?P<tune>{_alternation(_TUNE_TOKENS)}))?
    (?:_crf(?P<crf>\d+))?
    (?:_(?P<preset>{_alternation(_PRESET_TOKENS)}))?
    (?:_(?P<suffix>.+?))?
    \.(?P<ext>[A-Za-z0-9]+)$
""", re.VERBOSE)


@dataclass
class ParsedFilename:
    base: str
    width: int
    height: int
    codec: VideoCodec
    profile: str | None
    pix_fmt: PixFmt
    frame_rate: float
    matrix: ColorSpace | None
    color_range: ColorRange
    tune: str | None
    crf: int | None
    preset: str | None
    suffix: str | None
    ext: str

    def __str__(self) -> str:
        def fmt(value: object) -> str:
            if value is None:
                return "-"
            if isinstance(value, Enum):
                return f"{value.name} ({value.value})"
            return str(value)

        width = max(len(f.name) for f in fields(self))
        lines = [f"{f.name:<{width}} : {fmt(getattr(self, f.name))}" for f in fields(self)]
        return "\n".join(lines)




def parse_filename(filepath: str | Path) -> ParsedFilename:
    m = FILENAME_RE.match(Path(filepath).name)
    if m is None:
        raise ValueError(f"Filename does not match the expected format: {filepath}")
    g = m.groupdict()

    codec = _CODEC_BY_TOKEN[g["codec"]]
    profile = g["profile"]
    if codec == VideoCodec.DNXHR and profile is not None and not profile.startswith("dnxhr_"):
        profile = f"dnxhr_{profile}"

    return ParsedFilename(
        base=g["base"],
        width=int(g["width"]),
        height=int(g["height"]),
        codec=codec,
        profile=profile,
        pix_fmt=_PIXFMT_BY_TOKEN[g["pix_fmt"]],
        frame_rate=float(g["fps"]),
        matrix=_MATRIX_BY_TOKEN[g["matrix"]] if g["matrix"] else None,
        color_range=ColorRange(g["color_range"]),
        tune=g["tune"],
        crf=int(g["crf"]) if g["crf"] is not None else None,
        preset=g["preset"],
        suffix=g["suffix"],
        ext=g["ext"],
    )





def compare_vstream_to_filename(
    vstream: OutVideoStream, filepath: str | Path
) -> dict[str, tuple[object, object]]:
    """{field: (expected from vstream, found in filename)} for each mismatch. Empty = OK."""
    parsed = parse_filename(filepath)
    vcodec = vstream.codec
    h, w, _ = vstream.pipe_format.shape

    profile = effective_profile(vcodec, vstream.profile, vstream.pix_fmt)
    preset = effective_preset(vcodec, vstream.preset.value)
    matrix = vstream.color.matrix

    expected: dict[str, object] = {
        "width": w,
        "height": h,
        "codec": vcodec,
        "profile": str(profile) if profile is not None else None,
        "pix_fmt": vstream.pix_fmt,
        "matrix": matrix if isinstance(matrix, ColorSpace) else None,
        "color_range": effective_color_range(vstream.pix_fmt.value),
        "tune": effective_tune(vcodec, vstream.tune),
        "crf": effective_crf(vcodec, vstream.crf),
        "preset": preset.lower() if preset else None,
        # "suffix": generate_suffix(vstream=vstream) if vstream.suffix else None,
        "ext": vcodec_to_extension[vcodec].lstrip("."),
    }

    mismatches = {
        key: (value, getattr(parsed, key))
        for key, value in expected.items()
        if value != getattr(parsed, key)
    }

    # the filename keeps 3 decimals only (23.976 for 24000/1001)
    if abs(vstream.frame_rate - parsed.frame_rate) > 0.0006:
        mismatches["frame_rate"] = (vstream.frame_rate, parsed.frame_rate)

    return mismatches


