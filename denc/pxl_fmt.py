from enum import Enum
from hytils import red, lightgreen, darkgrey
import re
import subprocess

from .tools import ffmpeg_exe
from .dlogger import dlogger



class PixFmt(Enum):
    YUV420P = "yuv420p"
    YUV420P10 = "yuv420p10"
    YUV420P12 = "yuv420p12le"
    YUV422P = "yuv422p"
    YUV422P10 = "yuv422p10le"
    YUV422P12 = "yuv422p12le"
    YUV444P = "yuv444p"
    YUV444P10 = "yuv444p10le"
    YUV444P12 = "yuv444p12le"
    RGB24 = "rgb24"
    RGB48 = "rgb48le"
    RGBA24 = "rgba24"
    RGBA48 = "rgba48le"


RGB_PREFIXES = ("gbr", "bgr", "rgb")


def list_pixel_formats() -> dict[str, dict[str, bool | int | str]]:
    pixel_formats: dict[str, dict[str, bool | int | str]] = {}


    ffmpeg_command = [ffmpeg_exe, "-hide_banner", "-pix_fmts"]
    try:
        process = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE)
        ffmpeg_pixl_fmts: str = process.stdout.decode('utf-8')
    except:
        raise ValueError(red(f"Failed to get supported pixel formats"))


    _pixel_formats: list[str] | None = None
    if (
        _pixel_formats := re.findall(
            re.compile(r"[IOHBP.]{5}\s+([a-z_\d]+)\s+([1234]{1})\s+(\d+)\s+([\d-]+)"),
            ffmpeg_pixl_fmts
        )
    ):
        for f in _pixel_formats:
            k, nc, bpp, bit_depths = f

            _depths: list[int] = list(map(int, bit_depths.split('-')))

            nc = int(nc)
            pix_fmt: PixFmt
            if nc > 3:
                pix_fmt = PixFmt.RGBA48 if max(_depths) > 8 else PixFmt.RGBA24
            else:
                # Note: also convert from gray to rgb
                pix_fmt = PixFmt.RGB48 if max(_depths) > 8 else PixFmt.RGB24

            supported: bool = False
            if nc in (1, 3):
                supported: bool = True

            pixel_formats[k] = {
                'nc': nc,
                'bpp': bpp,
                'pipe_bpc': max(_depths),
                'pipe_bpp': sum(_depths),
                'pipe_pxl_fmt': pix_fmt,
                'supported': supported,
            }

    else:
        raise ValueError(red("Failed extracting pixel format"))

    return pixel_formats


PIXEL_FORMATS = list_pixel_formats()


# Debug
if False:
    for k, v in PIXEL_FORMATS.items():
        if v['supported']:
            msg: str = (
                f"{lightgreen(f"{k:<10}")}\tbpp={v['bpp']}, pipe_bpc={v['pipe_bpc']}, pipe_bpp={v['pipe_bpp']}, pipe_pxl_fmt={v['pipe_pxl_fmt']}"
            )
        else:
            msg: str = (
                f"{darkgrey(f"{k:<10}")}\tbpp={v['bpp']}, pipe_bpc={v['pipe_bpc']}, pipe_bpp={v['pipe_bpp']}, pipe_pxl_fmt={v['pipe_pxl_fmt']}"
            )
        print(msg)

