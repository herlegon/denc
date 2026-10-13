from fractions import Fraction
import multiprocessing
import os
from argparse import ArgumentParser
from decimal import Decimal
from pathlib import Path
from pprint import pformat, pprint
import signal
import sys
import time
from typing import Any
import numpy as np
from hytils import lightcyan, lightgreen, red, yellow

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
from tests.utils import check_generated_file


import torch



def file_exists_and_not_empty(filepath: str | Path) -> bool:
    p = Path(filepath)
    return p.is_file() and p.stat().st_size > 0


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
    parser.add_argument("--tune", action="store_true", required=False)
    args = parser.parse_args()
    all_tests: bool = not(any(x for x in [
        args.codec,
        args.pix_fmt,
        args.fps,
        args.crf,
        args.preset,
        args.color_space,
        args.color_range,
        args.tune,
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
        if not is_codec_supported(vcodec):
            print(lightcyan(f"\n{vcodec.value} :"), f"not supported")
            continue

        # if vcodec in (
        #     VideoCodec.H264,
        #     VideoCodec.H265,
        #     VideoCodec.FFV1,
        #     VideoCodec.DNXHR,
        #     VideoCodec.AV1,
        #     VideoCodec.VP9,
        #     VideoCodec.PRORES,
        #     VideoCodec.H264_NVENC,
        #     VideoCodec.HEVC_NVENC,
        # ):
        #     print(yellow(f"Ignore: {vcodec.value}"))
        #     continue

        if VCODEC_PROFILES.get(vcodec):
            for p in VCODEC_PROFILES[vcodec]:
                codec_profile_list.append((vcodec, p))
        else:
            codec_profile_list.append((vcodec, None))

    results: dict[str, tuple[bool, list[str]]] = {}


    # codec
    if args.codec or all_tests:
        print(lightcyan(f"CODECS\n{'-'*60}"))
        for vcodec, profile in codec_profile_list:
            vstream.codec = vcodec
            vstream.profile = profile
            vstream.pix_fmt = default_pixfmt_for_profile(vcodec=vcodec, profile=profile)
            vstream.shape = in_images[0].shape

            out_media.add_prop_suffix = True
            out_media.filepath = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"
            print(lightcyan(f"\n{vcodec.value}:"), out_media.filepath)
            denc.write(out_media, frames=out_frames)

            # Check generated media file
            out_fp: Path = out_media.filepath
            assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
            result_stdout = check_generated_file(out_media)
            results[out_fp.name] = result_stdout
            passed, stdout = result_stdout
            if not passed:
                break

        vstream.codec = default_settings['codec']


    # pixel Format
    if args.pix_fmt or all_tests:
        print(lightcyan(f"PIX_FMTS\n{'-'*60}"))
        for vcodec, profile in codec_profile_list:
            vstream.codec = vcodec
            vstream.shape = in_images[0].shape
            vstream.pix_fmt = default_settings['pix_fmt']
            out_media.add_prop_suffix = True
            filepath_template = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

            if vcodec == VideoCodec.DNXHR:
                profile_pixfmt = [(p, DNXHR_PROFILE_PIXFMT[p]) for p in DNXHR_PROFILE_PIXFMT]
            elif vcodec == VideoCodec.H265:
                profile_pixfmt = [(p, H265_PROFILE_PIXFMT[p]) for p in H265_PROFILE_PIXFMT]
            elif vcodec == VideoCodec.AV1:
                profile_pixfmt = [(p, AV1_PROFILE_PIXFMT[p]) for p in AV1_PROFILE_PIXFMT]
            elif vcodec == VideoCodec.VP9:
                profile_pixfmt = [(p, VP9_PROFILE_PIXFMT[p]) for p in VP9_PROFILE_PIXFMT]
            else:
                profile_pixfmt = [(None, pf) for pf in VCODEC_PIXFMTS[vcodec]]

            # print(profile_pixfmt)
            for profile, pix_fmts in profile_pixfmt:
                # print(lightcyan(f"{profile}: {pix_fmts}"))
                if isinstance(pix_fmts, list | tuple):
                    for pix_fmt in pix_fmts:
                        # print(lightcyan(f"          {profile}: {pix_fmt}"))
                        vstream.pix_fmt = pix_fmt
                        vstream.profile = profile
                        out_media.filepath = filepath_template
                        print(lightcyan(f"\n{vcodec.value}:"), pix_fmt)
                        denc.write(out_media, frames=out_frames)

                        # Check generated media file
                        out_fp: Path = out_media.filepath
                        assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
                        result_stdout = check_generated_file(out_media)
                        results[out_fp.name] = result_stdout
                        passed, stdout = result_stdout
                        if not passed:
                            break
                    if not passed:
                        break

                else:
                    vstream.pix_fmt = pix_fmts
                    vstream.profile = profile
                    out_media.filepath = filepath_template
                    print(lightcyan(out_media.filepath))
                    denc.write(out_media, frames=out_frames)
                    # Check generated media file
                    out_fp: Path = out_media.filepath
                    assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
                    result_stdout = check_generated_file(out_media)
                    results[out_fp.name] = result_stdout
                    passed, stdout = result_stdout
                    if not passed:
                        break


    # frame rates
    if args.fps or all_tests:
        print(lightcyan(f"FPS\n{'-'*60}"))
        out_media.add_prop_suffix = True
        filepath_template = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"
        vstream.pix_fmt = default_settings['pix_fmt']
        vstream.codec = default_settings['codec']

        for frame_rate in ("25", "50", "23.976", "29.97", "47.952", "59.94"):
            vstream.frame_rate = Fraction(frame_rate)
            vstream.is_frame_rate_fixed = True
            out_media.filepath = filepath_template
            print(lightcyan(f"\nFramerate:"), frame_rate)
            denc.write(out_media, frames=out_frames)
            # Check generated media file
            out_fp: Path = out_media.filepath
            assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
            result_stdout = check_generated_file(out_media)
            results[out_fp.name] = result_stdout
            passed, stdout = result_stdout
            if not passed:
                print(red("dfghjk"))
                break


    # crf
    if args.crf or all_tests:
        print(lightcyan(f"CRF\n{'-'*60}"))
        out_media.add_prop_suffix = True
        vstream.codec = VideoCodec.H265
        vstream.frame_rate = default_settings['frame_rate']
        vstream.profile = "main"
        vstream.pix_fmt = PixFmt.YUV420P
        filepath_template = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

        for crf in range(15, 35, 8):
            print(lightcyan(f"CRF:"), crf)
            vstream.crf = crf
            out_media.filepath = filepath_template
            print(lightcyan(out_media.filepath))
            denc.write(out_media, frames=out_frames)
            # Check generated media file
            out_fp: Path = out_media.filepath
            assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
            result_stdout = check_generated_file(out_media)
            results[out_fp.name] = result_stdout
            passed, stdout = result_stdout
            if not passed:
                break
        vstream.crf = default_settings['crf']


    # presets
    if args.preset or all_tests:
        print(lightcyan(f"PRESETS\n{'-'*60}"))
        out_media.add_prop_suffix = True
        filepath_template = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

        vstream.codec = VideoCodec.H265
        vstream.pix_fmt = PixFmt.YUV420P
        for preset in X26xPreset:
            vstream.preset = preset
            out_media.filepath = filepath_template
            print(lightcyan("Preset:"), vstream.preset.value)
            denc.write(out_media, frames=out_frames)
            # Check generated media file
            out_fp: Path = out_media.filepath
            assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
            result_stdout = check_generated_file(out_media)
            results[out_fp.name] = result_stdout
            passed, stdout = result_stdout
            if not passed:
                break

        # Verify it's unused with other codecs
        # vstream.codec = VideoCodec.DNXHR
        # vstream.preset = X26xPreset.MEDIUM
        # vstream.pix_fmt = PixFmt.YUV422P10
        # print(lightcyan("Preset:"), vstream.preset.value)


        vstream.preset = default_settings['preset']

    # tunes
    if args.tune or all_tests:
        print(lightcyan(f"TUNES\n{'-'*60}"))
        out_media.add_prop_suffix = True
        filepath_template = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

        vstream.codec = VideoCodec.H264
        vstream.pix_fmt = PixFmt.YUV420P
        vstream.preset = None
        for tune in VCODEC_TUNES[vstream.codec]:
            vstream.tune = tune
            out_media.filepath = filepath_template
            print(lightcyan(f"\nTune: {vstream.tune}"))
            denc.write(out_media, frames=out_frames)
            # Check generated media file
            out_fp: Path = out_media.filepath
            assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
            result_stdout = check_generated_file(out_media)
            results[out_fp.name] = result_stdout
            passed, stdout = result_stdout
            if not passed:
                break


        vstream.preset = default_settings['preset']


    # Color range
    if args.color_range or all_tests:
        print(lightcyan(f"COLOR RANGE\n{'-'*60}"))
        for vcodec, profile in codec_profile_list:
            vstream.codec = vcodec
            vstream.profile = profile
            vstream.tune = None
            vstream.pix_fmt = default_pixfmt_for_profile(vcodec=vcodec, profile=profile)

            out_media.add_prop_suffix = True
            filepath_template = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

            for color_range in ColorRange:
                vstream.color = ColorInfo(range=color_range)
                out_media.filepath = filepath_template
                print(lightcyan(out_media.filepath))
                print(lightcyan(f"\nColor range:"), color_range.value)
                denc.write(out_media, frames=out_frames)
                # Check generated media file
                out_fp: Path = out_media.filepath
                assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
                result_stdout = check_generated_file(out_media)
                results[out_fp.name] = result_stdout
                passed, stdout = result_stdout
                if not passed:
                    break


    # Color space
    if args.color_space or all_tests:
        print(lightcyan(f"COLOR SPACES\n{'-'*60}"))
        for vcodec in VideoCodec:
            if not is_codec_supported(vcodec):
                continue
            vstream.codec = vcodec
            profile = None
            if vcodec == VideoCodec.DNXHR:
                profile = "dnxhr_hq"
            vstream.profile = profile
            vstream.color = None
            vstream.pix_fmt = default_pixfmt_for_profile(vcodec=vcodec, profile=profile)

            out_media.add_prop_suffix = True
            filepath_template = out_dir / f"img_to_video{vcodec_to_extension[vstream.codec]}"

            for space in (
                # ColorSpace.UNKNOWN,
                ColorSpace.REC601_PAL,
                ColorSpace.REC601_NTSC,
                # ColorSpace.REC709,
                ColorSpace.BT709,
                # ColorSpace.BT2020NC,
                # ColorSpace.BT2020C,
            ):
                vstream.color = ColorInfo(
                    matrix=space, primaries=space, transfer=space
                )
                print()
                print()
                out_media.filepath = filepath_template
                print(lightcyan(out_media.filepath))
                print(lightcyan(f"\nColor space:"), space)
                denc.write(out_media, frames=out_frames)
                # Check generated media file
                out_fp: Path = out_media.filepath
                assert file_exists_and_not_empty(out_fp), f"Empty or missing: {out_fp}"
                result_stdout = check_generated_file(out_media)
                results[out_fp.name] = result_stdout
                passed, stdout = result_stdout
                if not passed:
                    break

    print("\nEnded.")


    for f_name, result_stdout in results.items():
        passed, stdout = result_stdout
        color = lightgreen if passed else red
        dlogger.info(f"{f_name:<100} {color(passed)}")
        if not passed:
            dlogger.info('\n'.join(stdout))



if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()

