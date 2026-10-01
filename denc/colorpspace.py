from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

from .vcodec import (
    VideoCodec
)
from .utils.utils import clean_str



class ColorSpace(Enum):
    UNKNOWN = "unknown"
    REC601_PAL = "rec601_pal"
    REC601_NTSC = "rec601_ntsc"
    REC709 = "bt709"
    BT709 = "bt709"
    BT2020NC = "bt2020nc"
    BT2020C = "bt2020c"



class ColorRange(str, Enum):
    LIMITED = "limited"
    FULL = "full"



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



@dataclass
class ColorInfo:
    matrix: str | ColorSpace | None = None
    primaries: str | None = None
    transfer: str | None = None
    range: ColorRange | None = None

    @property
    def has_complete_color_info(self) -> bool:
        return (
            self.matrix is not None
            and self.primaries is not None
            and self.transfer is not None
            and self.range is not None
        )


def ffmpeg_colorspace_args(
    colorspace: str | None,
    vcodec: VideoCodec,
) -> list[str]:
    args: list[str] = []
    if colorspace is not None:
        space, prim, trc = colorspace_to_params[colorspace]
        if vcodec == VideoCodec.H264:
            args = [
                "-x264-params",
                f"colormatrix={space}:colorprim={prim}:transfer={trc}"
            ]
            args.extend([
                "-colorspace", space,
                "-color_primaries", prim,
                "-color_trc", trc
            ])

        elif vcodec == VideoCodec.H265:
            args = [
                "-x265-params",
                f"colorprim={prim}:transfer={trc}:colormatrix={space}"
            ]

        elif vcodec == VideoCodec.DNXHR:
            args = [
                "-vf",
                clean_str(f"""
                    setparams=colorspace={space}
                        :color_primaries={prim}
                        :color_trc={trc}
                """),
            ]

    return args


def ffmpeg_color_range(color_range: ColorRange | None) -> list[str]:
    args: list[str] = []
    if color_range is not None:
        args = ["-color_range", color_range.value]

    return args
