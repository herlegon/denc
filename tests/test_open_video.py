from hytils import (
    absolute_path,
    lightcyan,
    red,
    yellow,
)
import os
from pprint import pprint
import re
import signal
import sys

import denc
from denc import (
    MediaStream,
    PIXEL_FORMATS,
    VideoCodec,
)


def main():

    in_video_dir: str = absolute_path(
        os.path.join(__file__, os.pardir, os.pardir, os.pardir, "benchmark")
    )

    in_videos: list[str] = sorted(
        [
            f
            for f in os.listdir(in_video_dir)
            # if f.endswith(".mkv") or f.endswith(".mxf")
            # if "smpte" in f
            # if f.endswith(".mxf")
            # if f.endswith(".mov")
            # if "FFv1" in f
        ]
    )

    filename_pattern = re.compile(r"""
        ^([^_]+)            # codec
        _(\d+)x(\d+)        # resolution width x height
        _([a-z0-9]+)        # pixel format
        (?:_([a-z0-9]+))?   # colorspace
        (?:_([a-z0-9]+))?   # (pal / ntsc / none)
        _(full|limited)     # range
        _([a-z0-9]+)        # pattern
        \.                 # extension
        """, re.VERBOSE
    )

    for f in in_videos:
        in_video_fp = os.path.join(in_video_dir, f)
        print(lightcyan(f"{f}"), end='')


        try:
            media: MediaStream = denc.open(in_video_fp)
            print(f"\t{media.video.pipe_format}", end='\t')
            # pprint(media.video)
        except Exception as e:
            print(red(f"\n\t{e}"))
            # media: MediaStream = denc.open(in_video_fp)
            continue
        print()

        if result := re.search(filename_pattern, f):
            file_codec, width, height, pix_fmt, color_space, ntsc_pal, color_range, video_pattern = result.groups()

            # Pixel Format
            _pix_fmt: str = 'rgb48le' if pix_fmt == 'rgb48' else pix_fmt
            _pix_fmt = 'rgba48le' if pix_fmt == 'rgba48' else _pix_fmt
            try:
                nc = PIXEL_FORMATS[pix_fmt]['nc']
            except Exception as e:
                print(red(f"{type(e)}. Not found:"), pix_fmt)
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
                print(red("Error: codec differs"), f"{media.video.codec}, must be {file_codec}")
                pprint(media.video)
                sys.exit()

            if media.video.shape != shape:
                print(red("Error: shape"), f"{media.video.shape}, must be {shape}")

            if media.video.color_space != color_space:
                if _codec == VideoCodec.FFV1.value.lower():
                    if color_space == 'gbr':
                        print(red("Error: color_space"), f"must be GBR for FFv1 codec")

                else:
                    if color_space == 'unknown' and media.video.color_space is not None:
                        print(red("Error: unknown color_space, found"), f"{media.video.color_space}")
                    else:
                        print(red("Error: color_space"), f"{media.video.color_space}, must be {color_space}")
                # pprint(media.video)
                # sys.exit()

            # _color_range = media.video.color_range.value
            if _codec == VideoCodec.PRORES.value.lower():
                if media.video.color_range is not None:
                    print(red("Error: color_range"), f"{media.video.color_range}, must be {color_range}")
                    pprint(media.video)
            else:
                try:
                    if media.video.color_range.value != color_range:
                        print(red("Error: color_range"), f"{media.video.color_range}, must be {color_range}")
                        pprint(media.video)
                        # sys.exit()

                except Exception as e:
                    print(e)
                    print(red("Error: color_range"), f"{media.video.color_range}, must be {color_range}")
                    # pprint(media.video)
                    # sys.exit()

        else:
            print(yellow("  can't verify using the filename"))

    print("Ended.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()

