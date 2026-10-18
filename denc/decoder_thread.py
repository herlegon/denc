from __future__ import annotations
import warnings
from threading import Event, Lock
import torch
from torch import Tensor
from torch.cuda import StreamContext

from hytils import lightgreen, red, yellow

from .base_thread import BaseThread, NnFrame
from .decoder import decoder_subprocess
from .dh_transfers import htod_transfer
from .media_stream import MediaStream
from .torch_tensor import img_to_tensor
from .vstream import (
    FShape,
    PipeFormat,
    VideoStream,
)


warnings.filterwarnings("ignore", category=UserWarning, message=".*non-writable tensors.*")


class DecoderThread(BaseThread):
    def __init__(
        self,
        media_stream: MediaStream,
        name: str | None = None,
        verbose: bool = False,
    ) -> None:
        super().__init__(name=name, verbose=verbose)
        self._decoded: int = 0
        self._stop_event: Event = Event()
        self._lock: Lock = Lock()
        self._lock.acquire(blocking=False)

        self.media_stream = media_stream
        self.d_subprocess, self.frame_count = decoder_subprocess(
            media_stream=self.media_stream
        )

    @property
    def decoded(self) -> int:
        return self._decoded


    @torch.inference_mode()
    def run(self) -> None:
        verbose = self.verbose

        if self.consumer is None:
            raise ValueError(red("[E] No consumer defined for the decoder."))

        d_stdout = self.d_subprocess.stdout

        vstream: VideoStream = self.media_stream.video
        pipe: PipeFormat = vstream.pipe_format
        nbytes: int = pipe.nbytes

        # Create a cuda stream and allocate Host memory
        cuda = bool("cuda" in vstream.device.name)
        if cuda:
            cuda_stream: torch.cuda.Stream = torch.cuda.Stream(vstream.device)
            stream_context: StreamContext = torch.cuda.stream(cuda_stream)
            host_mem: Tensor = torch.empty(nbytes, dtype=torch.uint8, pin_memory=True)

        else:
            from contextlib import nullcontext
            stream_context = nullcontext()

        # Input stream
        in_shape: FShape = pipe.shape
        in_dtype: torch.dtype = pipe.dtype
        in_nbytes = pipe.nbytes

        # Image to tensor
        tensor_dtype = vstream.device.dtype

        # Flow control
        remaining: int = self.media_stream.seek.count
        f_no: int = max(0, self.media_stream.seek.start)
        f_index: int = 0

        print(self.media_stream.seek)

        if verbose:
            print(lightgreen(f"[V][D] seek={self.media_stream.seek}"))
            print(lightgreen(
                f"[V][D] in_shape={in_shape}, in_dtype={in_dtype}, in_nbytes={in_nbytes}, remaining={remaining}"
            ))

        with stream_context:
            while (
                not self._stop_event.is_set()
                and remaining > 0
            ):
                # Decode a frame in CPU
                img_buffer: Tensor = torch.frombuffer(d_stdout.read(in_nbytes), dtype=torch.uint8)

                # Wait until resource (GPU) is available
                self._lock.acquire(blocking=True)
                if self._stop_event.is_set():
                    return

                if remaining < 0 or img_buffer is None:
                    print(yellow("remaining < 0 or img_buffer is None"))
                    remaining = 0
                    self.release()
                    break

                d_img: Tensor
                if cuda:
                    # HtoD transfer
                    d_img = htod_transfer(
                        host_mem=host_mem,
                        img_buffer=img_buffer,
                        img_dtype=in_dtype,
                        img_shape=in_shape,
                        cuda_stream=cuda_stream
                    )
                else:
                    d_img = img_buffer.view(dtype=in_dtype).view(in_shape)

                # Image to 4D tensor
                d_tensor: Tensor = img_to_tensor(d_img=d_img, tensor_dtype=tensor_dtype)

                # Create a frame object
                frame: NnFrame = NnFrame(
                    f_no=f_no,
                    tensor=d_tensor.clone(),
                    last=bool(remaining == 1)
                )
                if verbose:
                    print(
                        f"[V][D] ({lightgreen(f_index)}) ({f_no}), {remaining}. Tensor:",
                        f"{d_tensor.shape}, {d_tensor.dtype}"
                    )

                # Send the frame to the consumer
                self.consumer.put_frame(frame)

                remaining -= 1
                f_index += 1
                f_no += 1

        if self.verbose:
            print(lightgreen(f"[V][D] End of decoding"))


    def stop(self, force: bool=False) -> None:
        self._stop_event.set()

        if force:
            self.release()
            try:
                self.d_subprocess.kill()
            except:
                pass


    def release(self) -> None:
        try:
            self._lock.release()
        except:
            pass


    def set_produce_flag(self) -> None:
        self.release()

