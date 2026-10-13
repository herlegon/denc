from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from .pxl_fmt import RGB_PREFIXES
from .vcodec import (
    VideoCodec,
    PixFmt,
)

if TYPE_CHECKING:
    from .vstream import VideoStream



class ColorSpace(Enum):
    UNKNOWN = ""
    REC601_PAL = "rec601_pal"
    REC601_NTSC = "rec601_ntsc"
    REC709 = "bt709"
    BT709 = "bt709"
    BT2020NC = "bt2020nc"
    BT2020C = "bt2020c"

    BT470G = "bt470bg"
    SMPTE170M = "smpte170m"
    GAMMA28 = "gamma28"
    BT2020_10 = "bt2020-10"
    RGB = "gbr"


class ColorRange(str, Enum):
    AUTO = "auto"
    LIMITED = "limited" # davinci resolve: = video
    FULL = "full"



@dataclass
class ColorInfo:
    matrix: ColorSpace | None = None
    primaries: ColorSpace | None = None
    transfer: ColorSpace | None = None
    range: ColorRange | None = None

    @property
    def has_complete_color_info(self) -> bool:
        return (
            self.matrix is not None
            and self.primaries is not None
            and self.transfer is not None
            and self.range is not None
        )


def parse_color_range(value: str | None) -> ColorRange | None:
    if value in ("pc", "full"):
        return ColorRange.FULL

    if value in ("tv", "limited"):
        return ColorRange.LIMITED

    return None


def effective_color_range(out_pix_fmt: str) -> ColorRange:
    """Range really written: RGB outputs stay full, YUV outputs are limited."""
    return (
        ColorRange.FULL
        if out_pix_fmt.startswith(RGB_PREFIXES)
        else ColorRange.LIMITED
    )


def ffmpeg_color_range(
    vcodec: VideoCodec,
    out_pix_fmt: str,
) -> tuple[list[str], list[str]]:
    """Tag only. The pipe is RGB full range, ffmpeg's implicit conversion gives
    limited range for YUV outputs, and RGB outputs stay full."""
    range_value: str = effective_color_range(out_pix_fmt).value

    filters: list[str] = []
    args: list[str] = []

    if vcodec == VideoCodec.H265:
        args = ["-x265-params", f"range={range_value}"]
    elif vcodec == VideoCodec.DNXHR:
        filters.append(f"setparams=range={range_value}")
    else:
        args = ["-color_range", range_value]

    return filters, args


# ColorSpace.REC601_PAL     bt470bg     gamma28     bt470bg
# ColorSpace.REC601_NTSC    smpte170m   smpte170m   smpte170m
# ColorSpace.REC70          bt709       bt709       bt709
# ColorSpace.BT2020NC       bt2020      bt2020-10   bt2020-10
# ColorSpace.BT2020C        bt2020      bt2020-10   bt2020-10



colorspace_to_params = {
    # colorspace, primaries, transfer (trc)
    ColorSpace.UNKNOWN: ("unknown", "unknown", "unknown"),
    ColorSpace.REC601_PAL: ("bt470bg", "bt470bg", "gamma28"), # bt470bg for x265
    ColorSpace.REC601_NTSC: ("smpte170m", "smpte170m", "smpte170m"),
    ColorSpace.REC709: ("bt709", "bt709", "bt709"),
    ColorSpace.BT2020NC: ("bt2020nc", "bt2020", "bt2020-10"),
    ColorSpace.BT2020C: ("bt2020c", "bt2020", "bt2020-10"),
}
colorspace_to_params.update({
    ColorSpace.BT709: colorspace_to_params[ColorSpace.REC709]
})

# transfer names that differ between ffmpeg and x264/x265
X26X_TRANSFER: dict[str, str] = {"gamma28": "bt470bg"}

# gamma28 is only accepted by the generic -color_trc option.
# setparams, x264 and x265 call the same transfer bt470bg.
ALT_TRC_NAME: dict[str, str] = {"gamma28": "bt470bg"}


def ffmpeg_colorspace_args_(vstream: VideoStream) -> list[str]:
    # Modify the video stream color info
    colorspace: ColorSpace | None = vstream.color.matrix
    if colorspace is None or colorspace == ColorSpace.UNKNOWN:
        return []

    vcodec: VideoCodec = vstream.codec
    if (
        vcodec == VideoCodec.FFV1
        and vstream.pix_fmt in (
            PixFmt.RGB24,
            PixFmt.RGB48,
            PixFmt.RGBA24,
            PixFmt.RGBA48
        )
    ):
        vstream.color.matrix = ColorSpace.RGB
        vstream.color.primaries = None
        vstream.color.transfer = None
        return []

    space, prim, trc = colorspace_to_params[colorspace]
    alt_trc: str = ALT_TRC_NAME.get(trc, trc)

    # Modify the video stream with the params that will be used
    vstream.color.matrix = ColorSpace(space)
    vstream.color.primaries = ColorSpace(prim)
    vstream.color.transfer = ColorSpace(trc)

    args: list[str] = []
    if vcodec == VideoCodec.H264:
        args = ["-x264-params", f"colormatrix={space}:colorprim={prim}:transfer={alt_trc}"]

    elif vcodec == VideoCodec.H265:
        args = ["-x265-params", f"colormatrix={space}:colorprim={prim}:transfer={alt_trc}"]

    elif vcodec == VideoCodec.DNXHR:
        args = ["-vf", f"setparams=colorspace={space}:color_primaries={prim}:color_trc={alt_trc}"]

    args += ["-colorspace", space, "-color_primaries", prim, "-color_trc", trc]
    return args


not_supported_colorspace: dict[VideoCodec, list[ColorSpace]] = {
    VideoCodec.H264: [],
    VideoCodec.H265: [],
    VideoCodec.FFV1: [],
    VideoCodec.DNXHR: [ColorSpace.REC601_PAL, ColorSpace.REC601_NTSC],
    VideoCodec.VP9: [],
}
