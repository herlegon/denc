import logging

from hytils import (
    lightcyan,
    red,
    yellow,
)
import os
from pathlib import Path
from pprint import pformat, pprint
import re
import signal
import sys
sys.path.append(str(Path.cwd()))
import denc
from denc import (
    MediaStream,
    PIXEL_FORMATS,
    VideoCodec,
    dlogger
)


def main():

    dlogger.setLevel(logging.DEBUG)

    in_video_dir: Path = Path(__file__).resolve().parents[2] / "video-patterns"

    in_videos: list[Path] = sorted(
        [
            f
            for f in in_video_dir.iterdir()
            # if f.endswith(".mkv") or f.endswith(".mxf")
            # if "smpte" in f
            # if f.endswith(".mxf")
            # if f.endswith(".mov")
            # if "FFv1" in f
        ]
    )

    filename_pattern = re.compile(r"""
        ^([^_]+)            # pattern name (ex: smpte)
        _([^_]+)            # codec (ex: DNxHR)
        _(\d+)x(\d+)        # resolution width x height (ex: 1280x720)
        _([a-z0-9]+)        # pixel format (ex: yuv422p10le)
        (?:_([a-z0-9]+))?   # colorspace (ex: bt709)
        (?:_([a-z0-9]+))?   # (pal / ntsc / none / optional)
        _(full|limited)     # range (ex: limited)
        (?:_([a-z0-9]+))?   # pattern optional (si présent)
        \.([a-z0-9]+)$      # extension (ex: mxf)
        """, re.VERBOSE
    )

    for f in in_videos:
        in_video_fp: Path = in_video_dir / f
        dlogger.info(lightcyan(f"{f.name}"))

        try:
            media: MediaStream = denc.open(in_video_fp)
            dlogger.info(f"\t{media.video.pipe_format}")
            dlogger.info(pformat(media.video))

        except Exception as e:
            dlogger.error(red(f"\t{e}"))
            continue

        if result := re.search(filename_pattern, str(f.name)):
            result: re.Match
            (
                pattern_name,
                file_codec,
                width,
                height,
                pix_fmt,
                color_space,
                standard,  # pal/ntsc/none
                color_range,
                pattern,
                ext,
            ) = result.groups()

            # Pixel Format
            _pix_fmt: str = 'rgb48le' if pix_fmt == 'rgb48' else pix_fmt
            _pix_fmt = 'rgba48le' if pix_fmt == 'rgba48' else _pix_fmt
            try:
                nc = PIXEL_FORMATS[pix_fmt]['nc']

            except Exception as e:
                dlogger.error(red(f"{type(e)}. Not found:"), pix_fmt)
                pprint(media.video)
                sys.exit()

            # Shape
            shape = (int(height), int(width), nc)

            # Patch Codec
            _codec: str = (
                'h265'
                if media.video.codec.lower() == "hevc"
                else media.video.codec
            )

            # Tests:
            if _codec.lower() != file_codec.lower():
                dlogger.error(red("Error: codec differs") + f"{media.video.codec}, must be {file_codec}")
                pprint(media.video)
                sys.exit()

            if media.video.shape != shape:
                dlogger.error(red("Error: shape") + f"{media.video.shape}, must be {shape}")

            if media.video.color_space != color_space:
                if _codec == VideoCodec.FFV1.value.lower():
                    if color_space == 'gbr':
                        dlogger.error(red("Error: color_space") + f"must be GBR for FFv1 codec")

                else:
                    if color_space == 'unknown' and media.video.color_space is not None:
                        dlogger.error(red("Error: unknown color_space, found") + f"{media.video.color_space}")
                        sys.exit()
                    else:
                        dlogger.error(red("Error: color_space") + f"{media.video.color_space}, must be {color_space}")
                        sys.exit()
                # pprint(media.video)
                # sys.exit()

            # _color_range = media.video.color_range.value
            if _codec == VideoCodec.PRORES.value.lower():
                if media.video.color_range is not None:
                    dlogger.error(red("Error: color_range") + f"{media.video.color_range}, must be {color_range}")
                    pprint(media.video)
                    sys.exit()

            else:
                try:
                    if media.video.color_range.value != color_range:
                        dlogger.error(red("Error: color_range") + f"{media.video.color_range.value}, must be {color_range}")
                        pprint(media.video)
                        sys.exit()

                except Exception as e:
                    print(e)
                    dlogger.error(red("Error: color_range") + f"{media.video.color_range}, must be {color_range}")
                    # pprint(media.video)
                    sys.exit()

            dlogger.info(f"    OK")
        else:
            raise ValueError(red("  can't verify using the filename"))

    dlogger.info("Ended.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()

