from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .pxl_fmt import RGB_PREFIXES, PixFmt

from .vcodec import (
    VideoCodec
)


class ColorSpace(Enum):
    UNKNOWN = "unknown"
    REC601_PAL = "rec601_pal"
    REC601_NTSC = "rec601_ntsc"
    REC709 = "bt709"
    BT709 = "bt709"
    BT2020NC = "bt2020nc"
    BT2020C = "bt2020c"


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



colorspace_to_params = {
    # colorspace, primaries, transfer
    ColorSpace.UNKNOWN: ("unknown", "unknown", "unknown"),
    ColorSpace.REC601_PAL: ("bt470bg", "bt470bg", "gamma28"),
    ColorSpace.REC601_NTSC: ("smpte170m", "smpte170m", "smpte170m"),
    ColorSpace.REC709: ("bt709", "bt709", "bt709"),
    ColorSpace.BT2020NC: ("bt2020nc", "bt2020", "bt2020-10"),
    ColorSpace.BT2020C: ("bt2020c", "bt2020", "bt2020-10"),
}
colorspace_to_params.update({
    ColorSpace.BT709: colorspace_to_params[ColorSpace.REC709]
})



not_supported_colorspace: dict[VideoCodec, list[ColorSpace]] = {
    VideoCodec.H264: [],
    VideoCodec.H265: [],
    VideoCodec.FFV1: [],
    VideoCodec.DNXHR: [ColorSpace.REC601_PAL, ColorSpace.REC601_NTSC],
    VideoCodec.VP9: [],
}




def ffmpeg_colorspace_args(
    colorspace: ColorSpace | None,
    vcodec: VideoCodec,
) -> list[str]:
    args: list[str] = []
    if colorspace is not None:
        space, prim, trc = colorspace_to_params[colorspace]
        if vcodec == VideoCodec.H264:
            args = [
                "-x264-params", f"colormatrix={space}:colorprim={prim}:transfer={trc}"
            ]
            args.extend(
                ["-colorspace", space, "-color_primaries", prim, "-color_trc", trc]
            )

        elif vcodec == VideoCodec.H265:
            args = [
                "-x265-params", f"colorprim={prim}:transfer={trc}:colormatrix={space}"
            ]

        elif vcodec == VideoCodec.DNXHR:
            args = [
                "-vf", f"setparams=colorspace={space}:color_primaries={prim}:color_trc={trc}"
            ]

    return args
