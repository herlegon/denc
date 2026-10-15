from argparse import ArgumentParser
import logging
from pathlib import Path
import sys
from pprint import pprint
import signal

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import denc
from denc import (
    MediaStream,
    VideoCodec,
    PixFmt,
    ColorSpace,
    img_to_tensor,
    dlogger,
    vcodec_to_extension,
    is_codec_supported,
    VCODEC_PIXFMTS,
    DNXHR_PROFILE_PIXFMT,
    VCODEC_PROFILES,
    VCODEC_TUNES,
    X26xPreset,
    ColorRange,
    ColorInfo,
    default_pixfmt_for_profile,
    AV1_PROFILE_PIXFMT,
    H265_PROFILE_PIXFMT,
    VP9_PROFILE_PIXFMT
)


def main():
    dlogger.setLevel(logging.INFO)

    parser = ArgumentParser()
    parser.add_argument("--input", "-i", type=str, default="../../video-patterns/in.mxf", required=False)
    args = parser.parse_args()

    in_fp: Path = Path(args.input).resolve()
    file_media: MediaStream = denc.open(in_fp)
    pprint(file_media.video)


    out_media = file_media.copy()
    pprint(out_media.video)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()
