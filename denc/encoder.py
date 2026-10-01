from __future__ import annotations

from collections.abc import Callable
from hytils import purple, red
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

from .colorpspace import ColorSpace, ffmpeg_colorspace_args, ffmpeg_color_range
from .dh_transfers import dtoh_transfer
from .pxl_fmt import PIXEL_FORMATS
from .vstream import (
    FFmpegPreset,
    OutVideoStream,
    PipeFormat,
    VideoCodec,
)

from .vcodec import (
    vcodec_to_ffmpeg_vcodec,
    vcodec_output_opts,
    codec_platform_check,
    is_vaapi_codec,
    is_nvenc_codec,
    is_amf_codec,
)
from .utils.np_dtypes import np_to_uint16, np_to_uint8
from .utils.tools import ffmpeg_exe
from .utils.dlogger import dlogger
from .torch_tensor import (
    np_to_torch_dtype,
    tensor_to_img,
)
if TYPE_CHECKING:
    from .media_stream import MediaStream


# @dataclass(slots=True)
# class VideoEncoderParams:
#     filepath: str
#     # Complex filters
#     keep_sar: bool = True
#     size: tuple[int, int] | None = None
#     resize_algo: str = ''
#     add_borders: bool = False
#     # Encoder
#     encoder: VideoEncoder = VideoEncoder.H264
#     pix_fmt: str = 'yuv420p'
#     preset: str = 'medium'
#     tune: str = ''
#     crf: int = 15
#     overwrite: bool = True
#     encoder_settings: EncoderSettings | None = None
#     ffmpeg_args: str = ''
#     # Audio
#     copy_audio: bool = False
#     # Debug
#     benchmark: bool = False
#     verbose: bool = False



# def encoder_frame_prop(
#     shape: FShape,
#     pix_fmt: str,
#     fp32: bool = False,
# ) -> tuple[FShape, np.dtype, ChannelOrder, int, np.dtype] | None:
#     """Returns the shape, input dtype, channel order
#         size in bytes and output dtype of a frame to be encoded
#         fp32: force input dtype to float32, and channel order to bgr
#     """

#     # Encoder: pixel format
#     pixel_format = None
#     try:
#         pixel_format = PIXEL_FORMAT[pix_fmt]
#     except:
#         pass

#     # TODO: remove test of 'supported'
#     if (
#         pixel_format is None
#         or not pixel_format['supported']
#         or pixel_format['c_order'] == ''
#     ):
#         sys.exit(f"[E] {pix_fmt} is not a supported pixel format")

#     out_bpp, c_order = pixel_format['bpp'], pixel_format['c_order']
#     if out_bpp > 16:
#         sys.exit(f"[E] {pix_fmt} is not a supported pixel format (bpp>16)")
#     c_order = 'bgr' if 'bgr' in c_order or fp32 else 'rgb'

#     if 'f' in pixel_format:
#         sys.exit(f"[E] {pix_fmt} is not a supported pixel format (floating point)")
#     out_dtype: np.dtype = np.uint16 if out_bpp > 8 else np.uint8
#     in_dtype = np.float32 if fp32 else out_dtype

#     return (
#         shape,
#         in_dtype,
#         c_order,
#         math.prod(shape) * np.dtype(in_dtype).itemsize,
#         out_dtype
#     )



# def arguments_to_encoder_params(
#     arguments,
#     video_info: VideoInfo,
# ) -> VideoEncoderParams:
#     """Parse the command line to set the encoder parameters
#     """
#     # Encoder: encoder, settings
#     encoder: VideoEncoder = str_to_video_encoder[arguments.encoder]
#     encoder_settings: EncoderSettings | None = None
#     if encoder == VideoEncoder.FFV1:
#         encoder_settings = FFv1Settings()

#     # Extract pixfmt from ffmpeg_args
#     pix_fmt: str = arguments.pix_fmt
#     if (re_match := re.search(
#         re.compile(r"-pix_fmt\s([a-y0-9]+)"), arguments.ffmpeg_args)
#     ):
#         pix_fmt = re_match.group(1)
#     if pix_fmt not in PIXEL_FORMAT.keys():
#         sys.exit(red(f"Error: pixel format \"{pix_fmt}\" is not supported"))

#     # Create the encoder settings used by the encoder node
#     params: VideoEncoderParams = VideoEncoderParams(
#         filepath=video_info['filepath'],
#         encoder=encoder,
#         pix_fmt=pix_fmt,
#         preset=arguments.preset,
#         tune=arguments.tune,
#         crf=arguments.crf,
#         encoder_settings=encoder_settings,
#         ffmpeg_args=arguments.ffmpeg_args,
#         benchmark=arguments.benchmark,
#     )

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

    # # Encoder
    # if "-vcodec" not in params.ffmpeg_args:
    #     ffmpeg_command.extend(["-vcodec", f"{params.encoder.value}"])

    # if "-pix_fmt" not in params.ffmpeg_args:
    #     ffmpeg_command.extend(["-pix_fmt", f"{params.pix_fmt}"])

    # if "-preset" not in params.ffmpeg_args and params.preset:
    #     ffmpeg_command.extend(["-preset", f"{params.preset}"])

    # if "-tune" not in params.ffmpeg_args and params.tune:
    #     ffmpeg_command.extend(["-tune", f"{params.tune}"])

    # if "-crf" not in params.ffmpeg_args and params.crf != -1:
    #     ffmpeg_command.extend(["-crf", f"{params.crf}"])


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

    # # Output filepath
    # ffmpeg_command.append(params.filepath)
    # if params.overwrite:
    #     ffmpeg_command.append('-y')


def encoder_subprocess(
    vstream: OutVideoStream,
) -> subprocess.Popen | None:

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

    # Validate codec support on current platform
    valid, msg = codec_platform_check(vstream.codec)
    if not valid:
        raise RuntimeError(msg)

    # Profiles
    profile: list[str] = []
    profile_value = vstream.profile
    if profile_value:
        profile = ["-profile:v", profile_value]

    # Preset: not applicable for AV1, VP9, PRORES, or any hw-accel encoder
    preset_crf: list[str] = []
    _no_preset_codecs = (
        VideoCodec.AV1, VideoCodec.VP9, VideoCodec.PRORES,
        VideoCodec.H264_NVENC, VideoCodec.HEVC_NVENC, VideoCodec.AV1_NVENC,
        VideoCodec.H264_VAAPI, VideoCodec.H265_VAAPI,
        VideoCodec.AV1_VAAPI, VideoCodec.VP9_VAAPI,
        VideoCodec.H264_AMF, VideoCodec.HEVC_AMF,
    )
    if vstream.codec not in _no_preset_codecs:
        if vstream.preset != FFmpegPreset.DEFAULT:
            preset_crf.extend(["-preset", vstream.preset.value])

    # CRF: not applicable for DNXHR, PRORES, NVENC, VAAPI, or AMF encoders
    _no_crf_codecs = (
        VideoCodec.DNXHR, VideoCodec.PRORES,
        VideoCodec.H264_NVENC, VideoCodec.HEVC_NVENC, VideoCodec.AV1_NVENC,
        VideoCodec.H264_VAAPI, VideoCodec.H265_VAAPI,
        VideoCodec.AV1_VAAPI, VideoCodec.VP9_VAAPI,
        VideoCodec.H264_AMF, VideoCodec.HEVC_AMF,
    )
    if vstream.codec not in _no_crf_codecs:
        if vstream.crf >= 0:
            preset_crf.extend(["-crf", f"{vstream.crf}"])

    # extra params for codec
    codec_params: list[str] = vstream.extra_params.copy()

    # Colorspace (matrix, primaries, transfer)
    cs: ColorSpace | None = vstream.color.matrix if isinstance(vstream.color.matrix, ColorSpace) else None

    is_vaapi = is_vaapi_codec(vstream.codec)

    # Filter chain
    colorspace_filter: list[str] = []
    pix_fmt_args: list[str] = [] if is_vaapi else ["-pix_fmt", vstream.pix_fmt.value]
    if cs in (ColorSpace.BT2020NC, ColorSpace.BT2020C):
        colorspace_filter.append(f"format={vstream.pix_fmt.value}")
        pix_fmt_args = []  # handled by the filter

    if is_vaapi:
        # VAAPI requires uploading frames to hardware surfaces (format=nv12 or p010)
        hw_fmt = "p010" if "10" in vstream.pix_fmt.value else "nv12"
        colorspace_filter.append(f"format={hw_fmt}")
        colorspace_filter.append("hwupload")
        pix_fmt_args = []

    colorspace_args: list[str] = ffmpeg_colorspace_args(cs, vstream.codec)

    # DNXHR colorspace comes as a -vf filter from the helper — merge into filter chain
    if (
        vstream.codec == VideoCodec.DNXHR
        and colorspace_args
        and colorspace_args[0] == "-vf"
    ):
        colorspace_filter.append(colorspace_args[1])
        colorspace_args = []

    vf_args: list[str] = (["-vf", ",".join(colorspace_filter)] if colorspace_filter else [])

    # H265: merge x265-params from colorspace helper with extra log-level
    if vstream.codec == VideoCodec.H265:
        x265_value: str = "log-level=0"
        if colorspace_args and colorspace_args[0] == "-x265-params":
            x265_value = colorspace_args[1] + ":log-level=0"
            colorspace_args = []
        codec_params = ["-x265-params", x265_value] + codec_params

    # Color range
    color_range_args: list[str] = ffmpeg_color_range(vstream.color.range)

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
        # "-video_track_timescale", "60000",
        # "-time_base", "1/60000",
        *vcodec_output_opts.get(vstream.codec, []),
        *profile,
        *preset_crf,
        *codec_params,
        *colorspace_args,
        *color_range_args,
        # *metadata,
        str(vstream.filepath), "-y"
    ]


    dlogger.info(f"{purple("Encoder command:")} {' '.join(e_command)}")
    parent_dir: str = vstream.filepath.parent
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

    return e_subprocess



def _encode_cuda_tensors(
    media: MediaStream,
    frames: list[Tensor],
    device: str = "cuda:0",
) -> None:
    e_subprocess: subprocess.Popen = encoder_subprocess(vstream=media.video)

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

    e_subprocess = encoder_subprocess(vstream=media.video)

    def _e_thread(e_subprocess: subprocess.Popen, queue: Queue):
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

    _queue: Queue = Queue(maxsize=2)
    _thread = Thread(target=_e_thread, args=(e_subprocess, _queue))
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

