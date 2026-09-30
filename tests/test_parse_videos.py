import logging
from typing import Literal

from hytils import (
    lightcyan,
    lightgreen,
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

    results: dict[str, Literal['passed', 'failed']] = {}

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
        (?:_([0-9]+f))?     # number of frames
        \.([a-z0-9]+)$      # extension (ex: mxf)
        """, re.VERBOSE
    )

    for f in in_videos:
        in_video_fp: Path = in_video_dir / f
        f_name = str(f.name)
        dlogger.info(lightcyan(f"{f_name}"))

        try:
            media: MediaStream = denc.open(in_video_fp)
            dlogger.info(f"\t{media.video.pipe_format}")
            dlogger.info(pformat(media.video))

        except Exception as e:
            dlogger.error(red(f"\t{e}"))
            results[f_name] = 'failed'
            continue

        # pprint(media.video)

        if result := re.search(filename_pattern, str(f_name)):
            result: re.Match
            (
                pattern_name,
                f_codec,
                width,
                height,
                pix_fmt,
                f_color_space,
                standard,  # pal/ntsc/none
                color_range,
                pattern,
                f_frame_count,
                ext,
            ) = result.groups()

            # Pixel Format
            _pix_fmt: str = 'rgb48le' if pix_fmt == 'rgb48' else pix_fmt
            _pix_fmt = 'rgba48le' if pix_fmt == 'rgba48' else _pix_fmt
            try:
                nc = PIXEL_FORMATS[pix_fmt]['nc']

            except Exception as e:
                dlogger.error(red(f"{type(e)}. Not found:"), pix_fmt)
                results[f_name] = 'failed'
                pprint(media.video)
                sys.exit()

            # Shape
            shape = (int(height), int(width), nc)

            # Patch Codec
            m_codec = media.video.codec
            m_codec_str: str = (
                'h265'
                if m_codec in (VideoCodec.HEVC_NVENC, VideoCodec.HEVC_AMF)
                else m_codec.value
            )

            # Tests:
            if m_codec_str.lower() != f_codec.lower():
                dlogger.error(red("Error: codec differs") + f"{m_codec_str}, must be {f_codec}")
                pprint(media.video)
                results[f_name] = 'failed'
                sys.exit()

            if media.video.shape != shape:
                dlogger.error(red("Error: shape") + f"{media.video.shape}, must be {shape}")

            m_color_matrix = media.video.color.matrix
            if m_color_matrix != f_color_space:
                if f_codec == VideoCodec.FFV1.value.lower():
                    if f_color_space == 'gbr':
                        dlogger.error(red("Error: color_space ") + f"must be GBR for FFv1 codec")

                else:
                    if f_color_space == 'unknown' and m_color_matrix is not None:
                        dlogger.error(red("Error: unknown color_space, found ") + f"{m_color_matrix}")
                        results[f_name] = 'failed'
                        sys.exit()
                    elif f_color_space == 'unknwon' and m_color_matrix != "bt470bg":
                        dlogger.error(red("Error: color_space ") + f"{m_color_matrix}, must be {f_color_space}")
                        results[f_name] = 'failed'
                        sys.exit()
                # pprint(media.video)
                # sys.exit()

            # _color_range = media.video.color_range.value
            color_matrix = media.video.color.matrix
            if f_codec == VideoCodec.PRORES.value.lower():
                if color_matrix is not None:
                    dlogger.error(red("Error: color_range") + f"{v}, must be {color_range}")
                    pprint(media.video)
                    results[f_name] = 'failed'
                    sys.exit()

            else:
                try:
                    if media.video.color.range != color_range:
                        dlogger.error(red("Error: color_range") + f"{color_matrix}, must be {color_range}")
                        pprint(media.video)
                        results[f_name] = 'failed'
                        sys.exit()

                except Exception as e:
                    print(e)
                    dlogger.error(red("Error: color_range") + f"{color_matrix}, must be {color_range}")
                    # pprint(media.video)
                    results[f_name] = 'failed'
                    sys.exit()

            # frame count
            if f_frame_count:
                m_frame_count = media.video.frame_count
                if m_frame_count != f_frame_count:
                    dlogger.error(red("Error: frame count") + f"{m_frame_count}, must be {f_frame_count}")
                    results[f_name] = 'failed'

            dlogger.info(f"    OK")
            results[f_name] = 'passed'
        else:
            results[f_name] = 'failed'
            raise ValueError(red("  can't verify using the filename"))

    for f_name, r in results.items():
        color = lightgreen if r == 'passed' else red
        dlogger.info(f"{f_name:<60} {color(r)}")


    dlogger.info("Ended.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()

