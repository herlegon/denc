from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from hytils import lightgreen, purple, red, yellow
import numpy as np
import os
from pprint import pprint
from queue import Queue
import subprocess
import sys
from threading import Thread
import torch
from torch import Tensor
from torch.cuda import StreamContext
from typing import IO, TYPE_CHECKING

from .capabilities import is_codec_supported
from .color_space import ColorRange, ColorSpace, effective_color_range, ffmpeg_color_range, ffmpeg_colorspace_args
from .dh_transfers import dtoh_transfer
from .pxl_fmt import PIXEL_FORMATS, RGB_PREFIXES
from .vstream import (
    OutVideoStream,
    PipeFormat,
    VideoCodec,
)

from .vcodec import (
    VCODEC_PROFILES,
    CRF_RANGES,
    VCODECS_PRESETS,
    X26xPreset,
    to_ffmpeg_pixfmt,
    vcodec_to_ffmpeg_vcodec,
    vcodec_to_extension,
)
from .np_dtypes import np_to_uint16, np_to_uint8
from .tools import ffmpeg_exe
from .dlogger import dlogger
from .torch_tensor import (
    np_to_torch_dtype,
    tensor_to_img,
)
if TYPE_CHECKING:
    from .media_stream import MediaStream



def pretty_print_cmd(args: list[str]) -> str:
    lines = []
    current_line = []

    for item in args:
        if item.startswith("-"):
            # Si on commence une nouvelle option, on sauvegarde la ligne précédente
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [item]
        else:
            # Si on a déjà l'option + 1 argument, le 2e argument va à la ligne
            if len(current_line) >= 2:
                lines.append(" ".join(current_line))
                current_line = [item]
            else:
                current_line.append(item)

    if current_line:
        lines.append(" ".join(current_line))

    return "\n".join(lines)





def effective_profile(vcodec: VideoCodec, profile: str | None) -> str | None:
    """Profile really sent to ffmpeg, None if not applicable."""
    if (
        vcodec in VCODEC_PROFILES
        and profile in VCODEC_PROFILES[vcodec].available
    ):
        return profile
    return None



def effective_preset(vcodec: VideoCodec, preset: X26xPreset) -> X26xPreset | None:
    """Preset really sent to ffmpeg, None if not applicable."""
    if (
        preset is not None
        and vcodec in VCODECS_PRESETS
        and preset in VCODECS_PRESETS[vcodec]
    ):
        return preset
    return None



def effective_crf(vcodec: VideoCodec, crf: int) -> int | None:
    """CRF really sent to ffmpeg (clamped), None if the codec has no CRF."""
    if vcodec not in CRF_RANGES:
        return None
    lo, hi = CRF_RANGES[vcodec][:2]
    return max(lo, min(crf, hi))



def generate_encoder_command(vstream: OutVideoStream) -> list[str]:

    pipe: PipeFormat = vstream.pipe_format
    # pipe_pixel_format: dict = PIXEL_FORMATS[vstream.pix_fmt.value]['pipe_pxl_fmt']
    # if pipe_pixel_format in (PixFmt.RGB24, PixFmt.RGBA24):
    #     pipe.dtype = torch.uint8
    # elif pipe_pixel_format in (PixFmt.RGB48, PixFmt.RGBA48):
    #     pipe.dtype = torch.uint16
    # else:
    #     raise NotImplementedError(f"not supported: {pipe_pixel_format}")

    dlogger.info(f"""{purple("Encoder pipe:")}
          vstream.pix_fmt: {vstream.pix_fmt.value}
          shape: {pipe.shape}
          dtype: {pipe.dtype}
          pixfmt: {pipe.pix_fmt}
          nbytes: {pipe.nbytes}"""
        .replace("    ", " ")
    )

    vcodec: VideoCodec = vstream.codec

    # Validate codec support on current platform
    if not is_codec_supported(vcodec):
        raise ValueError(f"Not a supported video codec: `{vcodec.value}`")

    # Pixel format
    ffmpeg_pix_fmt: str = to_ffmpeg_pixfmt(vcodec=vcodec, pixfmt=vstream.pix_fmt)
    pix_fmt_args: list[str] = ["-pix_fmt", ffmpeg_pix_fmt]

    # Profiles
    profile = effective_profile(vcodec, vstream.profile)
    profile_args: list[str] = ["-profile:v", profile] if profile else []

    # Preset: not applicable for AV1, VP9, PRORES, or any hw-accel encoder
    preset_value = effective_preset(vcodec, vstream.preset)
    preset_args: list[str] = ["-preset", preset_value.value] if preset_value else []

    # crf range
    crf = effective_crf(vcodec, vstream.crf)
    crf_args: list[str] = ["-crf", str(crf)] if crf is not None else []
    if vcodec == VideoCodec.VP9:
        crf_args.extend(["-b:v", "0"])

    # params for codec:
    vcodec_options: list[str] = []
    if vstream.codec_options is not None:
        vcodec_options = vstream.codec_options.to_arg_list()


    # extra params for codec
    codec_params: list[str] = vstream.extra_params.copy()

    # Colorspace tags (matrix, primaries, transfer)
    color_space: ColorSpace | None = (
        vstream.color.matrix if isinstance(vstream.color.matrix, ColorSpace) else None
    )
    colorspace_args: list[str] = ffmpeg_colorspace_args(color_space, vcodec)

    # Color range: conversion filters + tag
    # Color range: the requested value is only honored when it matches what is encoded
    requested_range: ColorRange | None = vstream.color.range
    effective_range: ColorRange = effective_color_range(ffmpeg_pix_fmt)
    if requested_range not in (None, ColorRange.AUTO, effective_range):
        dlogger.warning(yellow(
            f"Color range `{requested_range.value}` ignored for pix_fmt "
            f"`{ffmpeg_pix_fmt}`: encoded as `{effective_range.value}`"
        ))

    range_filters, color_range_args = ffmpeg_color_range(
        vcodec=vcodec, out_pix_fmt=ffmpeg_pix_fmt
    )

    # Single -vf: range filters, plus the DNxHR colorspace tag (setparams)
    vf_filters: list[str] = list(range_filters)
    if colorspace_args and colorspace_args[0] == "-vf":
        vf_filters.append(colorspace_args[1])
        colorspace_args = []
    vf_args: list[str] = ["-vf", ",".join(vf_filters)] if vf_filters else []

    # Single -x265-params: log-level + colorspace + range
    if vcodec == VideoCodec.H265:
        x265_values: list[str] = ["log-level=0"]
        for tag_args in (colorspace_args, color_range_args):
            if tag_args and tag_args[0] == "-x265-params":
                x265_values.append(tag_args[1])
        colorspace_args, color_range_args = [], []
        codec_params = ["-x265-params", ":".join(x265_values)] + codec_params


    # AUDIO
    #     # Copy audio stream if no video clipping
    #     if (
    #         arguments.ss == ''
    #         and arguments.to == ''
    #         and arguments.t == ''
    #     ):
    #         params.copy_audio = True

    #     return params

    # if params.copy_audio and in_media_info['audio']['nstreams'] > 0:
    #     ffmpeg_command.extend(['-i', video_info['filepath']])

    # ffmpeg_command.extend([
    #     "-map", "0:v"
    # ])


    # if params.benchmark:
    #     ffmpeg_command.extend(["-benchmark", "-f", "null", "-"])
    #     return ffmpeg_command


    # # Audio/subtitles
    # if params.copy_audio and True:
    #     if in_media_info['audio']['nstreams'] > 0:
    #         ffmpeg_command.extend([
    #             "-map", "1:a", "-acodec", "copy"
    #         ])
    #     if in_media_info['subtitles']['nstreams'] > 0:
    #         ffmpeg_command.extend([
    #             "-map", "2:s", "-scodec", "copy"
    #         ])

    # # Custom params
    # if params.ffmpeg_args:
    #     ffmpeg_command.extend(params.ffmpeg_args.split(" "))


    # Add suffix (mainly used for unitary tests)
    filepath = vstream.filepath
    if vstream.parent.add_prop_suffix:
        suffix = generate_video_basename_suffix(vstream=vstream)
        filepath = filepath.with_name(f"{filepath.stem}_{suffix}{filepath.suffix}")

    # Create command as a list
    h, w = pipe.shape[:2]
    e_command: list[str] = [
        ffmpeg_exe,
        "-hide_banner",
        "-loglevel", "warning",
        "-stats",

        "-f", "rawvideo",
        "-pixel_format", pipe.pix_fmt,
        "-video_size", f"{w}x{h}",
        "-r", str(vstream.frame_rate),

        "-i", "pipe:0",

        *vf_args,
        *pix_fmt_args,
        "-vcodec", vcodec_to_ffmpeg_vcodec[vstream.codec],
        *vcodec_options,

        *profile_args,
        *crf_args,
        *preset_args,
        *codec_params,
        *colorspace_args,
        *color_range_args,
        # *metadata,
        str(filepath), "-y"
    ]

    dlogger.debug(f"{purple("Encoder command:")} {' '.join(e_command)}")
    dlogger.debug(f"{purple("Encoder command:")}")
    dlogger.debug(pretty_print_cmd(e_command))

    return e_command



def _encode_cuda_tensors(
    media: MediaStream,
    frames: list[Tensor],
    device: str = "cuda:0",
) -> None:
    e_command = generate_encoder_command(vstream=media.video)
    parent_dir: str = media.video.filepath.parent
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    e_subprocess: subprocess.Popen | None = None
    try:
        e_subprocess = subprocess.Popen(
            e_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except Exception as e:
        dlogger.error(red(f"Unexpected error: {type(e)}"))
        return None

    # Output stream
    pipe: PipeFormat = media.video.pipe_format
    img_dtype: np.dtype = pipe.dtype

    # Create a cuda stream and allocate Host memory
    cuda_stream: torch.cuda.Stream = torch.cuda.Stream(device)
    stream_context: StreamContext = torch.cuda.stream(cuda_stream)
    host_mem: Tensor = torch.empty(
        pipe.shape,
        dtype=np_to_torch_dtype(img_dtype),
        pin_memory=True
    )

    def _encoder_thread(
        queue: Queue,
        e_subprocess: subprocess.Popen,
    ):
        while True:
            # Wait for a frame or a poison pill
            out_img = queue.get(block=True)
            if out_img is None:
                break

            try:
                e_subprocess.stdin.write(out_img)
            except:
                print(f"failed send {type(out_img)}")
                stdout: str = e_subprocess.stdout.read().decode("utf-8")
                pprint(stdout.split('\n'))
                break


    _queue: Queue = Queue(maxsize=2)
    _thread = Thread(
        target=_encoder_thread,
        args=(_queue, e_subprocess)
    )
    _thread.start()

    with stream_context:
        for d_tensor in frames:
            d_img: Tensor = tensor_to_img(tensor=d_tensor, img_dtype=img_dtype)

            out_img: np.ndarray = dtoh_transfer(
                host_mem=host_mem,
                d_img=d_img,
                cuda_stream=cuda_stream
            )

            _queue.put(out_img)

    _queue.put(None)
    _thread.join()
    stdout_bytes: bytes | None = None
    stdout_bytes, _ = e_subprocess.communicate(timeout=30)
    if stdout_bytes is not None:
        stdout = stdout_bytes.decode('utf-8)')
        if stdout:
            print(f"stdout:")
            print(stdout)



def _encoder_thread(e_subprocess: subprocess.Popen, queue: Queue):
    stream: IO = e_subprocess.stdin
    os.set_blocking(e_subprocess.stdout.fileno(), False)
    line: str = e_subprocess.stdout.readline().decode('utf-8')
    if line:
        print(line.strip(), end='\r', file=sys.stdout)

    while True:
        out_img: np.ndarray = queue.get()
        if out_img is None:
            break
        try:
            stream.write(out_img)
            # if e_subprocess.poll() is None:
            #     break
            line = e_subprocess.stdout.readline().decode('utf-8')
            if line:
                print(line.strip(), end='\r', file=sys.stdout)
        except:
            pass



def write(
    media: MediaStream,
    frames: list[np.ndarray | Tensor],
) -> None:
    """Create a video from a set of images
    frames must be in rgb order
    """
    # Use the first image
    img0 = frames[0]

    pipe: PipeFormat = media.video.pipe_format
    if isinstance(img0, Tensor):
        _, c, h, w = img0.shape
        pipe.shape = (h, w, c)
        if "cuda" in img0.device.type:
            _encode_cuda_tensors(media=media, frames=frames, device=img0.device)
            return
    else:
        pipe.shape = img0.shape

    # Sync filepath: media.filepath may have been set after construction
    if media.filepath is not None:
        from pathlib import Path
        media.video.filepath = Path(media.filepath) if not isinstance(media.filepath, Path) else media.filepath

    # Generate the FFmpeg command
    e_command = generate_encoder_command(vstream=media.video)
    # And create the subprocess
    parent_dir: str = media.video.filepath.parent
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    e_subprocess: subprocess.Popen | None = None
    try:
        e_subprocess = subprocess.Popen(
            e_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except Exception as e:
        dlogger.error(red(f"Unexpected error: {type(e)}"))
        return None

    _queue: Queue = Queue(maxsize=2)
    _thread = Thread(target=_encoder_thread, args=(e_subprocess, _queue))
    _thread.start()

    if isinstance(img0, Tensor):
        for tensor in frames:
            img = tensor_to_img(tensor=tensor, img_dtype=pipe.dtype).numpy()
            _queue.put(img)

    else:
        if pipe.dtype == torch.uint16:
            convert_fct: Callable = np_to_uint16
        elif pipe.dtype == torch.uint8:
            convert_fct: Callable = np_to_uint8
        else:
            raise NotImplementedError(red(f"{pipe.dtype} is not a valid dtype for encoder pipe"))
        for img in frames:
            _queue.put(np.ascontiguousarray(convert_fct(img)))

    _queue.put(None)
    _thread.join()

    stdout_bytes: bytes | None = None
    stdout_bytes, _ = e_subprocess.communicate(timeout=30)
    if stdout_bytes is not None:
        stdout = stdout_bytes.decode('utf-8)')
        # TODO: parse the output file
        if stdout:
            print(f"stdout:")
            pprint(stdout)
            if 'error' in stdout.lower():
                raise RuntimeError(f"FFmpeg error:\n{stdout}")





def generate_video_basename_suffix(vstream: OutVideoStream) -> str:
    vcodec = vstream.codec

    frame_rate_str = (
        f"{int(vstream.frame_rate)}fps"
        if vstream.frame_rate.is_integer()
        else f"{float(vstream.frame_rate):.03f}fps"
    )

    h, w, _ = vstream.pipe_format.shape

    matrix = vstream.color.matrix
    matrix_str = matrix.value if isinstance(matrix, ColorSpace) else matrix  # str | None

    crf = effective_crf(vcodec, vstream.crf)
    preset = effective_preset(vcodec, vstream.preset)
    profile = effective_profile(vcodec, vstream.profile)

    # None / empty parts are skipped
    parts: list[str | None] = [
        f"{w}x{h}",
        vcodec.value.lower(),
        profile.replace("dnxhr_", "") if profile else None,
        vstream.pix_fmt.value,
        frame_rate_str,
        matrix_str,
        effective_color_range(vstream.pix_fmt.value).value,
        f"crf{crf}" if crf is not None else None,
        preset.value.lower() if preset else None,
    ]

    suffix = "_".join(str(p) for p in parts if p if p is not None)
    return suffix
