import os
import numpy as np
from pprint import pprint
from queue import Queue
import subprocess
from threading import Thread
import torch
from torch import Tensor
from torch.cuda import StreamContext
from typing import TYPE_CHECKING
import warnings

from .media_stream import MediaStream
from .np_dtypes import np_to_float32
from .tools import ffmpeg_exe
from .torch_tensor import (
    torch_dtype_to_np,
    np_to_torch_dtype,
)
from .vstream import (
    PipeFormat,
    VideoStream,
    DecoderResize,
)


warnings.filterwarnings("ignore", category=UserWarning, message=".*non-writable tensors.*")


_is_pynnlib_available: bool = False
try:
    if os.path.exists("pynnlib"):
        _is_pynnlib_available = True
except:
    pass

if not _is_pynnlib_available:
    from .torch_tensor import (
        Idtype,
        IdtypeToTorch,
        np_to_torch_dtype,
        img_to_tensor,
    )
else:
    import importlib
    _pynnlib = importlib.import_module("pynnlib")
    Idtype = _pynnlib.Idtype
    IdtypeToTorch = _pynnlib.IdtypeToTorch
    np_to_torch_dtype = _pynnlib.np_to_torch_dtype

if TYPE_CHECKING:
    from .torch_tensor import (
        Idtype,
        IdtypeToTorch,
        np_to_torch_dtype,
        img_to_tensor,
    )
from .dh_transfers import htod_transfer



def _clean_vfilter(line: str) -> str:
    cleaned: str = line
    for c in ('\\', '\"', ' ', '\r', '\n'):
        cleaned = cleaned.replace(c, '')
    return cleaned.strip()



def decoder_subprocess(media_stream: MediaStream) -> tuple[subprocess.Popen, int]:
    vstream: VideoStream = media_stream.video
    pipe: PipeFormat = vstream.pipe_format

    seek_start: list[str] = []
    if media_stream.seek.start > 0:
        seek_start = ["-ss", media_stream.seek.start_hms]

    seek_duration: list[str] = []
    frame_count = vstream.frame_count
    if media_stream.seek.count > 0:
        seek_duration = ["-t", media_stream.seek.duration]
        frame_count = media_stream.seek.count

    vfilter: list[str] = []
    resize: DecoderResize = vstream.resize
    resize_algo = 'lanczos'
    w, h = "in_w", "in_h"
    if resize.use_sar:
        resize_algo = vstream.resize.algorithm
        h, w = vstream.shape[:2]
        if resize.side == 'width':
            w = int(vstream.sar.numerator * w / vstream.sar.denominator)
        else:
            h = int(vstream.sar.denominator * h / vstream.sar.numerator)

    if resize.enabled:
        raise NotImplementedError(red("resize with FFmpeg"))

    vfilter_str: str = f"""scale={w}:{h}:sws_flags={resize_algo}
        + full_chroma_int
        + full_chroma_inp
        + accurate_rnd
        + bitexact
    """
    vfilter = ["-vf", _clean_vfilter(vfilter_str)]


    d_command: list[str] = [
        ffmpeg_exe,
        "-hide_banner",
        "-loglevel", "warning",
        "-nostats",
        *seek_start,
        "-i", vstream.filepath,
        *seek_duration,

        *vfilter,

        "-f", "image2pipe",
        "-pix_fmt", pipe.pix_fmt,
        "-vcodec", "rawvideo",
        "-"
    ]
    print(lightcyan(f"  d_command:"), " ".join(d_command))

    d_subprocess: subprocess.Popen = None
    try:
        d_subprocess = subprocess.Popen(
            d_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except Exception as e:
        print(red(f"[E][W] Unexpected error: {type(e)}"))

    return d_subprocess, frame_count



def _decode_frames_as_cuda_tensors(
    media_stream: MediaStream,
    device: str = "cuda",
    tensor_dtype: torch.dtype | Idtype = 'fp32',
    threaded: bool = True,
) -> list[Tensor]:

    if not isinstance(tensor_dtype, torch.dtype):
        tensor_dtype = IdtypeToTorch[tensor_dtype]

    pipe: PipeFormat = media_stream.video.pipe_format
    nbytes: int = pipe.nbytes

    # CUDA: stream and host mem allocation
    cuda_stream: torch.cuda.Stream = torch.cuda.Stream(device)
    stream_context: StreamContext = torch.cuda.stream(cuda_stream)
    host_mem: Tensor = torch.empty(
        nbytes, dtype=torch.uint8, pin_memory=True
    )

    if threaded:
        def _htod_transfer(
            queue: Queue,
            pipe: PipeFormat,
            device: str,
            cuda_stream,
            tensors: list[Tensor],
        ):
            img_dtype: torch.dtype = np_to_torch_dtype(pipe.dtype)
            while True:
                img_buffer: Tensor = queue.get()
                if img_buffer is None:
                    break

                # HtoD transfer
                d_img: Tensor = htod_transfer(
                    host_mem=host_mem,
                    img_buffer=img_buffer,
                    img_dtype=img_dtype,
                    img_shape=pipe.shape,
                    cuda_stream=cuda_stream,
                    device=device,
                )

                # Image to 4D tensor
                d_tensor: Tensor = img_to_tensor(d_img=d_img, tensor_dtype=tensor_dtype)
                tensors.append(d_tensor)

    d_subprocess, frame_count = decoder_subprocess(media_stream)
    tensors: list[Tensor] = []
    with stream_context:

        if threaded:
            _queue: Queue = Queue(maxsize=2)
            _thread = Thread(
                target=_htod_transfer,
                args=(_queue, pipe, device, cuda_stream, tensors)
            )
            _thread.start()

            for _ in range(frame_count):
                _queue.put(
                    torch.frombuffer(d_subprocess.stdout.read(nbytes), dtype=torch.uint8)
                )
            _queue.put(None)
            _thread.join()

        else:
            img_dtype: torch.dtype = np_to_torch_dtype(pipe.dtype)
            for i in range(frame_count):
                frame_buffer: Tensor = torch.frombuffer(
                    d_subprocess.stdout.read(nbytes), dtype=torch.uint8,
                )

                # HtoD transfer
                d_img: Tensor = htod_transfer(
                    host_mem=host_mem,
                    img_buffer=frame_buffer,
                    img_dtype=img_dtype,
                    img_shape=pipe.shape,
                    cuda_stream=cuda_stream,
                    device=device
                )

                # Image to 4D tensor
                d_tensor: Tensor = img_to_tensor(d_img=d_img, tensor_dtype=tensor_dtype)

                print(
                    f"[V][D] ({lightgreen(i)}) Tensor: {d_tensor.shape}, {d_tensor.dtype}"
                )
                tensors.append(d_tensor)

    return tensors



def decode_frames(
    media_stream: MediaStream,
    to_device: str = "cpu",
    as_tensor: bool = False,
    tensor_dtype: np.dtype | torch.dtype | Idtype = 'fp32',
    threaded: bool = True,
) -> list[np.ndarray] | list[Tensor]:


    pipe: PipeFormat = media_stream.video.pipe_format
    media_stream.video.set_device(device=to_device, dtype=tensor_dtype)

    if "cuda" in to_device:
        if not torch.cuda.is_available():
            raise SystemError(red(f"No cuda device"))
        return _decode_frames_as_cuda_tensors(
            media_stream=media_stream,
            device=to_device,
            tensor_dtype=tensor_dtype,
            threaded=threaded,
        )
    elif to_device != 'cpu':
        raise ValueError(red(f"Not a valid device: {to_device}"))

    if not isinstance(tensor_dtype, torch.dtype):
        tensor_dtype = IdtypeToTorch[tensor_dtype]

    if as_tensor and tensor_dtype != torch.float32:
        raise ValueError(red(f"Cannot load frames in cpu with dtype={tensor_dtype}. Must be fp32 (torch.float32)"))

    nbytes: int = pipe.nbytes
    d_subprocess, frame_count = decoder_subprocess(media_stream=media_stream)

    in_frames: list[np.ndarray] = []

    if not as_tensor:
        dtype: np.dtype = torch_dtype_to_np(pipe.dtype)
        if threaded:
            def _np_to_float32_thread(
                queue: Queue,
                pipe: PipeFormat,
                dtype: np.dtype,
                frames: list[np.ndarray],
            ):
                while True:
                    frame_buffer: np.ndarray = queue.get()
                    if frame_buffer is None:
                        break
                    frames.append(
                        np.ascontiguousarray(
                            np_to_float32(
                                frame_buffer.view(dtype=dtype).reshape(pipe.shape)
                            )
                        )
                    )

            _queue: Queue = Queue(maxsize=2)
            _thread = Thread(
                target=_np_to_float32_thread,
                args=(_queue, pipe, dtype, in_frames)
            )
            _thread.start()

            for _ in range(frame_count):
                _queue.put(
                    np.frombuffer(d_subprocess.stdout.read(nbytes), dtype=np.uint8)
                )
            _queue.put(None)
            _thread.join()

        else:
            for _ in range(frame_count):
                in_frames.append(
                    np.ascontiguousarray(
                        np_to_float32(
                            np.frombuffer(d_subprocess.stdout.read(nbytes), dtype=np.uint8)
                            .view(dtype=dtype)
                            .reshape(pipe.shape)
                        )
                    )
                )

    else:
        if threaded:
            def _buffer_to_tensor_thread(
                queue: Queue,
                pipe: PipeFormat,
                tensor_dtype: torch.dtype,
                frames: list[np.ndarray],
            ):
                np_dtype: np.dtype = torch_dtype_to_np(pipe.dtype)
                while True:
                    frame_buffer: np.ndarray = queue.get()
                    if frame_buffer is None:
                        break
                    frames.append(
                        img_to_tensor(
                            d_img=frame_buffer.view(dtype=np_dtype).reshape(pipe.shape),
                            tensor_dtype=tensor_dtype
                        )
                    )

            _queue: Queue = Queue(maxsize=2)
            _thread = Thread(
                target=_buffer_to_tensor_thread,
                args=(_queue, pipe, tensor_dtype, in_frames)
            )
            _thread.start()

            for _ in range(frame_count):
                _queue.put(
                    torch.frombuffer(d_subprocess.stdout.read(nbytes), dtype=torch.uint8)
                )
            _queue.put(None)
            _thread.join()

        else:
            for _ in range(frame_count):
                d_img: Tensor = torch.frombuffer(
                    d_subprocess.stdout.read(nbytes), dtype=torch.uint8
                ).view(dtype=pipe.dtype).reshape(pipe.shape)

                in_frames.append(img_to_tensor(d_img=d_img, tensor_dtype=tensor_dtype))



    # if d_subprocess.poll() is None:
    #     timeout: int = 10
    #     while d_subprocess.poll() is None and timeout:
    #         time.sleep(0.1)
    #         timeout -= 1
    #     if timeout:
    #         print(f"    killed decoder")
    #         d_subprocess.kill()
    return in_frames
