from argparse import ArgumentParser
from decimal import Decimal
from enum import Enum, IntEnum
from fractions import Fraction
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
sys.path.append(str(Path(__file__).resolve().parent.parent))
from denc.time_conversions import FrameRate
from hytils import lightcyan, purple

import denc
from denc import (
    VideoCodec,
    PixFmt,
    ColorSpace,
    ColorRange,
    MediaStream,
    generate_encoder_command,
    dlogger,
    InputPattern,
)
from denc.encoder import pretty_print_cmd






def main():
    # denc_logger.addHandler(logging.StreamHandler(sys.stdout))
    dlogger.setLevel("DEBUG")

    parser = ArgumentParser()
    parser.add_argument(
        "--duration",
        "-t",
        type=float,
        default=40,
        required=False,
        help="Duration in seconds, default: 60",
    )
    parser.add_argument(
        "--out_dir",
        "-o",
        type=str,
        default="",
        required=False,
        help="Output directory, default: `../../video-patterns`",
    )
    parser.add_argument(
        "--resolution",
        type=str,
        default="720x540",
        required=False,
        help="Resolution",
    )

    args = parser.parse_args()

    if args.out_dir:
        out_dir: Path = Path(args.out_dir).resolve()
    else:
        out_dir: Path = Path(__file__).resolve().parents[2] / "video-patterns"


    out_media: MediaStream = denc.new(filepath=out_dir / "smpte")
    # out_media.container = '.mxf'
    out_media.add_prop_suffix = True
    vstream = out_media.video
    vstream.codec = VideoCodec.H265
    vstream.color.matrix = ColorSpace.BT709
    vstream.pix_fmt = PixFmt.YUV422P10
    vstream.frame_rate = FrameRate(25, 1)
    vstream.from_pattern = InputPattern.SMPTEHDBARS

    vstream.duration = Decimal(f"{args.duration}")

    resolution: list[int] = args.resolution.split("x")
    vstream.shape = (int(resolution[1]), int(resolution[0]), 3)

    ffmpeg_command = generate_encoder_command(media=out_media)
    dlogger.debug(f"{purple("Encoder command:")}\n{subprocess.list2cmdline(ffmpeg_command)}")
    dlogger.debug(f"{purple("Encoder command:")}")
    dlogger.debug(pretty_print_cmd(ffmpeg_command))


    result = subprocess.run(
        ffmpeg_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    for std in (result.stdout, result.stderr):
        std_str: str = ''
        try:
            std_str = std.decode('utf-8')
        except:
            pass
        if std_str:
            print(std_str)
            # for l in std_str:
            #     if not l.startswith("x265 [info]"):
            #         print(l.strip())


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()



