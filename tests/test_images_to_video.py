from fractions import Fraction
import multiprocessing
import os
from argparse import ArgumentParser
from decimal import Decimal
from pathlib import Path
from pprint import pprint
import signal
import sys
import time
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from hytils import lightcyan, red

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
    RGB_PREFIXES,
    X26xPreset,
    ColorRange,
    ColorInfo,
    default_pixfmt_for_profile,
)
from denc.profiles import AV1_PROFILE_PIXFMT, H265_PROFILE_PIXFMT, VP9_PROFILE_PIXFMT

import torch


# def generate_filename(media: MediaStream) -> str:
#     vstream = media.video

#     frame_rate_str = (
#         f"{int(vstream.frame_rate)}fps"
#         if vstream.frame_rate.is_integer()
#         else f"{float(vstream.frame_rate):.03f}fps"
#     )

#     h, w, _ = vstream.pipe_format.shape
#     pix_fmt: str = vstream.pix_fmt.value
#     color_range = vstream.color.range
#     if (
#         not pix_fmt.startswith(RGB_PREFIXES)
#         and vstream.color.range == ColorRange.FULL
#     ):
#         color_range = ColorRange.LIMITED

#     filename: str = "_".join(map(str,[
#         vstream.codec.value.lower(),
#         f"{w}x{h}",
#         frame_rate_str,
#         vstream.pix_fmt.value,
#         vstream.color.matrix.value if isinstance(vstream.color.matrix, ColorSpace) else str(vstream.color.matrix),
#         color_range.value,
#         f"crf{vstream.crf}",
#         vstream.preset.value.lower(),
#     ])) + vcodec_to_extension[vstream.codec]

#     return filename


def main():
    # denc_logger.addHandler(logging.StreamHandler(sys.stdout))
    dlogger.setLevel("DEBUG")

    cpu_count: int = int(3 * multiprocessing.cpu_count() / 4)

    parser = ArgumentParser()
    parser.add_argument("--codec", action="store_true", required=False)
    parser.add_argument("--pix_fmt", action="store_true", required=False)
    parser.add_argument("--fps", action="store_true", required=False)
    parser.add_argument("--crf", action="store_true", required=False)
    parser.add_argument("--color_space", action="store_true", required=False)
    parser.add_argument("--color_range", action="store_true", required=False)
    parser.add_argument("--preset", action="store_true", required=False)
    args = parser.parse_args()
    all_tests: bool = not(any(x for x in [
        args.codec,
        args.pix_fmt,
        args.fps,
        args.crf,
        args.preset,
        args.color_space,
        args.color_range,
    ]))


    # a list of images
    in_img_dir: Path = Path(__file__).resolve().parents[2] / "imgs" / "denc" / "in"
    in_img_fp = sorted(Path(in_img_dir).glob("*.png"))[:50]

    start_time = time.time()
    in_images = denc.load_images(
        filepaths=in_img_fp,
        cpu_count=cpu_count,
        dtype=np.float32
    )
    elapsed = time.time() - start_time
    print(f"[np.float32] loaded {len(in_images)} images in {1000 * (elapsed):.01f}ms ({len(in_images)/elapsed:.01f}fps) (cpu_count={cpu_count})")

    out_frames: list[np.ndarray] = list([
        img_to_tensor(d_img=torch.from_numpy(img), tensor_dtype=torch.float32, flip_r_b=True)
        for img in in_images
    ])

    # Write images as video
    print(lightcyan(f"h264"))
    out_media: MediaStream = denc.new()
    vstream = out_media.video
    vstream.color.matrix = ColorSpace.REC709

    default_settings: dict[str, Any] = {
        'codec': VideoCodec.H264,
        'pix_fmt': PixFmt.YUV420P,
        'frame_rate': 25,
        'crf': 22,
        'preset': X26xPreset.VERYFAST
    }
    vstream.codec = default_settings['codec']
    vstream.pix_fmt = default_settings['pix_fmt']
    vstream.frame_rate = default_settings['frame_rate']
    vstream.crf = default_settings['crf']
    vstream.preset = default_settings['preset']
    # vstream.profile = "main"
    # vstream.set_device(device=device, dtype=torch.float32)

    # pipe_format is not valid yet because it depends on the tensor
    # could be set using vstream.set_pipe_format or wait for the encoder to set it
    # print(vstream.pipe_format)
    vstream.shape = in_images[0].shape
    vstream.set_pipe_format(torch.uint8)
    print(vstream.pipe_format)
    print(vstream.shape)
    # print(vstream.codec)
    out_dir: Path = Path(__file__).resolve().parents[1] / "out" / "img_to_video"

    codec_profile_list: list[tuple[VideoCodec, str]] = []
    for vcodec in VideoCodec:
        # if vcodec in (
        #     VideoCodec.H264,
        #     VideoCodec.H265,
        #     VideoCodec.FFV1,
        #     VideoCodec.DNXHR,
        # ):
        #     continue
        if not is_codec_supported(vcodec):
            print(lightcyan(f"\n{vcodec.value} :"), f"not supported")
            continue

        # if vcodec not in (VideoCodec.DNXHR, VideoCodec.H265,):
        #     codec_profile_list.append((vcodec, None))

        if VCODEC_PROFILES.get(vcodec):
            for p in VCODEC_PROFILES[vcodec]:
                codec_profile_list.append((vcodec, p))
        else:
            codec_profile_list.append((vcodec, None))

    pprint(codec_profile_list)


    # codec
    if args.codec or all_tests:

        for vcodec, profile in codec_profile_list:
            if not is_codec_supported(vcodec):
                print(lightcyan(f"\n{vcodec.value}:"), f"not supported")
                continue
            vstream.codec = vcodec
            vstream.profile = profile
            vstream.pix_fmt = default_pixfmt_for_profile(vcodec=vcodec, profile=profile)

            out_media.add_prop_suffix = True
            out_media.filepath = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"
            print(lightcyan(f"\n{vcodec.value}:"), out_media.filepath)
            denc.write(out_media, frames=out_frames)
        vstream.codec = default_settings['codec']
        vstream.pix_fmt = default_settings['pix_fmt']

    # pixel Format
    if args.pix_fmt or all_tests:
        for vcodec in codec_profile_list:
            vstream.codec = vcodec
            out_media.add_prop_suffix = True
            out_media.filepath = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

            if vcodec == VideoCodec.DNXHR:
                profile_pixfmt = [(p, DNXHR_PROFILE_PIXFMT[p]) for p in DNXHR_PROFILE_PIXFMT]
            elif vcodec == VideoCodec.H265:
                profile_pixfmt = [(p, H265_PROFILE_PIXFMT[p]) for p in H265_PROFILE_PIXFMT]
            elif vcodec == VideoCodec.AV1:
                profile_pixfmt = [(p, AV1_PROFILE_PIXFMT[p]) for p in AV1_PROFILE_PIXFMT]
            elif vcodec == VideoCodec.VP9:
                profile_pixfmt = [(p, VP9_PROFILE_PIXFMT[p]) for p in VP9_PROFILE_PIXFMT]
            else:
                profile_pixfmt = [(pf, None) for pf in VCODEC_PIXFMTS[vcodec]]

            for profile, pix_fmt in profile_pixfmt:
                vstream.pix_fmt = pix_fmt
                vstream.profile = profile
                print(lightcyan(out_media.filepath))
                denc.write(out_media, frames=out_frames)
            vstream.codec = default_settings['codec']
            vstream.pix_fmt = default_settings['pix_fmt']

    # frame rates
    if args.fps or all_tests:
        out_media.add_prop_suffix = True
        out_media.filepath = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

        for frame_rate in ("25", "50", "23.976", "29.97", "47.952", "59.94"):
        # for frame_rate in (59.94, ):
            vstream.frame_rate = Fraction(frame_rate)
            print(lightcyan(out_media.filepath))
            denc.write(out_media, frames=out_frames)
        vstream.frame_rate = default_settings['frame_rate']

    # crf
    if args.crf or all_tests:
        out_media.add_prop_suffix = True
        out_media.filepath = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"
        for crf in range(15, 35, 8):
            vstream.crf = crf
            print(lightcyan(out_media.filepath))
            denc.write(out_media, frames=out_frames)
        vstream.crf = default_settings['crf']

    # presets
    if args.preset or all_tests:
        out_media.filepath = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"
        out_media.add_prop_suffix = True

        vstream.codec = VideoCodec.H265
        for preset in X26xPreset:
            vstream.preset = preset
            print(lightcyan("Preset:"), vstream.preset.value)
            denc.write(out_media, frames=out_frames)

        # Verify it's unused with other codecs
        vstream.codec = VideoCodec.DNXHR
        vstream.preset = X26xPreset.MEDIUM
        vstream.pix_fmt = PixFmt.YUV422P10
        print(lightcyan("Preset:"), vstream.preset.value)
        denc.write(out_media, frames=out_frames)

        vstream.preset = default_settings['preset']

    # Color range
    if args.color_range or all_tests:
        for vcodec in VideoCodec:
            vstream.codec = vcodec
            if not is_codec_supported(vcodec):
                print(lightcyan(f"\n{vcodec.value} :"), f"not supported")
                continue

            if vcodec == VideoCodec.DNXHR:
                combos = [(DNXHR_PROFILE_PIXFMT[p], p) for p in DNXHR_PROFILE_PIXFMT]
            else:
                combos = [(pf, None) for pf in VCODEC_PIXFMTS[vcodec]]

            out_media.add_prop_suffix = True
            out_media.filepath = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

            for pix_fmt, profile in combos:
                vstream.pix_fmt = pix_fmt
                vstream.profile = profile

                for color_range in ColorRange:
                    vstream.color = ColorInfo(range=color_range)
                    print(lightcyan(f"\nColor range:"), color_range.value)
                    denc.write(out_media, frames=out_frames)


            vstream.codec = default_settings['codec']
            vstream.pix_fmt = default_settings['pix_fmt']

    # print(lightcyan(f"h265"))
    # out_media.video.filepath = "h265_yuv422p10_rec709_veryfast.mkv"
    # vstream.codec = VideoCodec.H265
    # vstream.pix_fmt = PixFmt.YUV422P10
    # denc.write(out_media, frames=out_frames)




    print("\nEnded.")



if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()

