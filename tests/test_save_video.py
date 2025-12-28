from argparse import ArgumentParser
from hytils import (
    absolute_path,
    lightcyan
)
import logging
import multiprocessing
import os
from pprint import pprint
import re
import signal
import sys
import time
from typing import Any

import numpy as np

import denc
from denc import (
    MediaStream,
    VideoCodec,
    PixFmt,
    ColorSpace,
    FFmpegPreset,
    img_to_tensor,
    denc_logger,
    vcodec_to_extension,
)
import torch


def generate_filename(media: MediaStream) -> str:
    vstream = media.video

    frame_rate_str = (
        f"{int(vstream.frame_rate)}fps"
        if vstream.frame_rate.is_integer()
        else f"{float(vstream.frame_rate):.03f}fps"
    )

    h, w, _ = vstream.pipe_format.shape

    filename: str = "_".join(map(str,[
        vstream.codec.value.lower(),
        f"{w}x{h}",
        frame_rate_str,
        vstream.pix_fmt.value,
        vstream.color_space.value,
        f"crf{vstream.crf}",
        vstream.preset.value.lower(),
    ])) + vcodec_to_extension[vstream.codec]

    return filename


def main():
    # denc_logger.addHandler(logging.StreamHandler(sys.stdout))
    denc_logger.setLevel("DEBUG")

    cpu_count: int = int(3 * multiprocessing.cpu_count() / 4)

    parser = ArgumentParser()
    parser.add_argument("--codec", action="store_true", required=False)
    parser.add_argument("--pix_fmt", action="store_true", required=False)
    parser.add_argument("--fps", action="store_true", required=False)
    parser.add_argument("--crf", action="store_true", required=False)
    parser.add_argument("--preset", action="store_true", required=False)
    args = parser.parse_args()
    all_tests: bool = not(any(x for x in [
        args.codec,
        args.fps,
        args.crf,
        args.preset,
        args.pix_fmt,
    ]))


    # a list of images
    if sys.platform == 'linux':
        in_img_dir: str = absolute_path(f"~/z-personnel/mco/imgs/ep10_226_lr_j")
    else:
        in_img_dir: str = absolute_path(f"N:\\imgs\\ep01_215_upscale_j")

    in_img_fp: list[str] = sorted(
        [os.path.join(in_img_dir, f) for f in os.listdir(in_img_dir) if f.endswith(".png")]
    )
    in_img_fp = in_img_fp[:50]

    start_time = time.time()
    in_images = denc.load_images(
        filepaths=in_img_fp, cpu_count=cpu_count, dtype=np.float32
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
    vstream.color_space = ColorSpace.REC709

    default_settings: dict[str, Any] = {
        'codec': VideoCodec.H264,
        'pix_fmt': PixFmt.YUV420P,
        'frame_rate': 25,
        'crf': 22,
        'preset': FFmpegPreset.VERYFAST
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


    # codec
    if args.codec or all_tests:
        codecs: list[VideoCodec] = list([c for c in VideoCodec])

        codecs = [
            # VideoCodec.H264,
            # VideoCodec.H265,
            # VideoCodec.FFV1,
            # VideoCodec.DNXHR,
            # VideoCodec.AV1,
            # VideoCodec.VP9,
            # VideoCodec.PRORES,
            # VideoCodec.H264_VULKAN,
            # VideoCodec.H264_NVENC,
            # VideoCodec.H265_NVENC,
            # VideoCodec.HEVC_NVENC,
            # VideoCodec.AV1_NVENC,
            VideoCodec.H264_VAAPI,
            VideoCodec.H265_VAAPI,
            VideoCodec.AV1_VAAPI,
            VideoCodec.VP9_VAAPI,
        ]

        pprint(codecs)
        for codec in codecs:
            vstream.codec = codec
            # if codec in (
            #     VideoCodec.H264,
            #     # VideoCodec.H264_VULKAN,
            # ):
            #     vstream.pix_fmt = PixFmt.YUV420P
            # else:
            #     vstream.pix_fmt = PixFmt.YUV422P10


            out_media.filepath = generate_filename(out_media)
            print(lightcyan(f"{codec.value} :"), out_media.filepath)
            denc.write(out_media, frames=out_frames)
        vstream.codec = default_settings['codec']
        vstream.pix_fmt = default_settings['pix_fmt']

    # pixel Format
    if args.pix_fmt or all_tests:
        vstream.codec = VideoCodec.H265
        pix_fmts: list[PixFmt] = list([p for p in PixFmt])
        # H.265: rgb48le -> gbrp12le; rgb24 -> gbrp
        for pix_fmt in pix_fmts:
            if 'a' in pix_fmt.value:
                continue
            vstream.pix_fmt = pix_fmt
            out_media.filepath = generate_filename(out_media)
            print(lightcyan(out_media.filepath))
            denc.write(out_media, frames=out_frames)
        vstream.codec = default_settings['codec']
        vstream.pix_fmt = default_settings['pix_fmt']


    # frame rates
    if args.fps or all_tests:
        for frame_rate in (25, 50, 23.976, 29.97, 47.952, 59.94):
        # for frame_rate in (59.94, ):
            vstream.frame_rate = frame_rate
            out_media.filepath = generate_filename(out_media)
            print(lightcyan(out_media.filepath))
            denc.write(out_media, frames=out_frames)
        vstream.frame_rate = default_settings['pix_fmt']


    # crf
    if args.crf or all_tests:
        for crf in range(15, 35, 8):
            out_media.filepath = generate_filename(out_media)
            print(lightcyan(out_media.filepath))
            denc.write(out_media, frames=out_frames)
        vstream.crf = default_settings['crf']


    # presets
    if args.preset or all_tests:
        for preset in FFmpegPreset:
            vstream.preset = preset
            out_media.filepath = generate_filename(out_media)
            print(lightcyan(out_media.filepath))
            denc.write(out_media, frames=out_frames)
        vstream.preset = default_settings['preset']





    # print(lightcyan(f"h265"))
    # out_media.video.filepath = "h265_yuv422p10_rec709_veryfast.mkv"
    # vstream.codec = VideoCodec.H265
    # vstream.pix_fmt = PixFmt.YUV422P10
    # denc.write(out_media, frames=out_frames)




    print("Ended.")



if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()

