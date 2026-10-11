from enum import Enum
from pprint import pformat, pprint
import re
from dataclasses import dataclass, fields
from pathlib import Path
import signal
import sys

from hytils import lightcyan, lightgreen, red

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import denc
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
    dlogger,
    MediaStream,
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





def check_generated_file(out_media: MediaStream) -> tuple[bool, list[str]]:
    stdout: list[str] = []
    vstream = out_media.video

    print(lightcyan(f"\nParse generated file"))
    file_media: MediaStream = denc.open(out_media.filepath)

    stdout.append(f"\nInput\n{'-'*32}")
    stdout.append(pformat(out_media.video))

    stdout.append(f"\nGenerated\n{'-'*32}")
    file_vstream = file_media.video
    stdout.append(pformat(file_vstream))
    stdout.append("")

    COLUMN_WIDTH: int = 18
    ROW_HEADER_WIDTH: int = 20

    total_width = ROW_HEADER_WIDTH + (COLUMN_WIDTH * 2) + 10
    header = (
        f"{' ':<{ROW_HEADER_WIDTH}} | {'Input':<{COLUMN_WIDTH}}  |  {'Generated':<{COLUMN_WIDTH}}"
    )
    stdout.append(f"{header}\n{"-" * total_width}")

    h, w, in_nc = vstream.shape
    in_shape_str = f"{w} x {h}"
    h, w, file_nc = file_vstream.shape
    file_shape_str = f"{w} x {h}"
    stdout.append(f"{'shape':<{ROW_HEADER_WIDTH}} | {in_shape_str:<{COLUMN_WIDTH}}  |  {file_shape_str}")
    stdout.append(f"{'channels':<{ROW_HEADER_WIDTH}} | {in_nc:<{COLUMN_WIDTH}}  |  {file_nc}")
    stdout.append(f"{'codec':<{ROW_HEADER_WIDTH}} | {vstream.codec:<{COLUMN_WIDTH}}  |  {file_vstream.codec}")
    stdout.append(f"{'profile':<{ROW_HEADER_WIDTH}} | {vstream.profile:<{COLUMN_WIDTH}}  |  {file_vstream.profile}")
    stdout.append(f"{'pix fmt':<{ROW_HEADER_WIDTH}} | {vstream.pix_fmt:<{COLUMN_WIDTH}}  |  {file_vstream.pix_fmt}")

    stdout.append(f"{'is frame rate fixed':<{ROW_HEADER_WIDTH}} | {vstream.is_frame_rate_fixed:<{COLUMN_WIDTH}}  |  {file_vstream.is_frame_rate_fixed}")
    stdout.append(f"{'frame rate (r)':<{ROW_HEADER_WIDTH}} | {vstream.frame_rate_r:<{COLUMN_WIDTH}}  |  {file_vstream.frame_rate_r}")
    stdout.append(f"{'frame rate (avg)':<{ROW_HEADER_WIDTH}} | {vstream.frame_rate_avg:<{COLUMN_WIDTH}}  |  {file_vstream.frame_rate_avg}")

    stdout.append(f"{'duration':<{ROW_HEADER_WIDTH}} | {vstream.duration:<{COLUMN_WIDTH}}  |  {file_vstream.duration}")
    stdout.append(f"{'frame count':<{ROW_HEADER_WIDTH}} | {vstream.frame_count:<{COLUMN_WIDTH}}  |  {file_vstream.frame_count}")

    stdout.append(f"{'matrix':<{ROW_HEADER_WIDTH}} | {vstream.color.matrix:<{COLUMN_WIDTH}}  |  {file_vstream.color.matrix}")
    stdout.append(f"{'primary':<{ROW_HEADER_WIDTH}} | {vstream.color.primaries:<{COLUMN_WIDTH}}  |  {file_vstream.color.primaries}")
    stdout.append(f"{'transfer':<{ROW_HEADER_WIDTH}} | {vstream.color.transfer:<{COLUMN_WIDTH}}  |  {file_vstream.color.transfer}")


    in_range = vstream.color.range
    stdout.append(f"{'range':<{ROW_HEADER_WIDTH}} | {in_range if in_range else '':<{COLUMN_WIDTH}}  |  {file_vstream.color.range}")

    in_sar_str = f"{vstream.sar.numerator}:{vstream.sar.denominator}"
    file_sar_str = f"{file_vstream.sar.numerator}:{file_vstream.sar.denominator}"
    stdout.append(f"{'sar':<{ROW_HEADER_WIDTH}} | {in_sar_str:<{COLUMN_WIDTH}}  |  {file_sar_str}")
    in_dar_str = f"{vstream.dar.numerator}:{vstream.dar.denominator}"
    file_dar_str = f"{file_vstream.dar.numerator}:{file_vstream.dar.denominator}"
    stdout.append(f"{'dar':<{ROW_HEADER_WIDTH}} | {in_dar_str:<{COLUMN_WIDTH}}  |  {file_dar_str}")
    stdout.append(f"{'interlaced':<{ROW_HEADER_WIDTH}} | {vstream.interlaced:<{COLUMN_WIDTH}}  |  {file_vstream.interlaced}")


    passed = True
    if file_vstream.codec != vstream.codec:
        stdout.append(red(f"Erroneous codec"))
        passed = False

    if file_vstream.profile != vstream.profile:
      stdout.append(red(f"Erroneous profile"))
      passed = False

    if file_vstream.pix_fmt != vstream.pix_fmt:
      stdout.append(red(f"Erroneous pix_fmt"))
      passed = False

    if file_vstream.color.range != vstream.color.range:
      stdout.append(red(f"Erroneous color range"))
      passed = False

    if file_vstream.color.matrix != vstream.color.matrix:
      stdout.append(red(f"Erroneous matrix"))
      passed = False

    if file_vstream.color.primaries != vstream.color.primaries:
      stdout.append(red(f"Erroneous primaries"))
      passed = False

    if file_vstream.color.transfer != vstream.color.transfer:
      stdout.append(red(f"Erroneous transfer"))
      passed = False

    if file_vstream.shape != vstream.shape:
      stdout.append(red(f"Erroneous shape"))
      passed = False

    if file_vstream.is_frame_rate_fixed != vstream.is_frame_rate_fixed:
      stdout.append(red(f"Erroneous IS frame rate"))
      passed = False

    if file_vstream.frame_rate_avg != vstream.frame_rate_avg:
      stdout.append(red(f"Erroneous frame rate avg"))
      passed = False

    if file_vstream.frame_rate_r != vstream.frame_rate_r:
      stdout.append(red(f"Erroneous frame rate r"))
      passed = False

    if file_vstream.sar != vstream.sar:
      stdout.append(red(f"Erroneous sar"))
      passed = False

    if file_vstream.dar != vstream.dar:
      stdout.append(red(f"Erroneous dar"))
      passed = False

    if file_vstream.interlaced != vstream.interlaced:
      stdout.append(red(f"Erroneous interlaced"))
      passed = False

    if file_vstream.duration != vstream.duration:
      stdout.append(red(f"Erroneous duration"))
      passed = False

    if file_vstream.frame_count != vstream.frame_count:
        stdout.append(red(f"Erroneous frame count"))
        passed = False

    # TODO verify color space

    return passed, stdout
