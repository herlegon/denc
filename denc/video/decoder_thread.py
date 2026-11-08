from __future__ import annotations
import io
import warnings
from threading import Event, Lock
import torch
from torch.cuda import StreamContext
from torch import Tensor

from hytils import lightcyan, red

from ..base_thread import DEC_ENC_HOST_NBUFFERS, BaseThread, NnFrame
from ..decoder import decoder_subprocess
from ..dh_transfers import htod_transfer
from ..media_stream import MediaStream
from ..torch_tensor import img_to_tensor
from ..vstream import (
    FShape,
    PipeFormat,
    VideoStream,
)
from ..nnframe import mark_frame_ready, wait_frame_ready
from ..dlogger import dlogger

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

    def run(self) -> None:
        try:
            self.decode()

        except Exception as e:
            dlogger.error(red(f"[E] {str(e)}"))


    @torch.inference_mode()
    def decode(self) -> None:
        verbose = self.verbose

        if self.consumer is None:
            raise ValueError(red("[E] No consumer defined for the decoder."))

        d_stdout: io.BufferedReader = self.d_subprocess.stdout
        vstream: VideoStream = self.media_stream.video
        pipe: PipeFormat = vstream.pipe_format
        nbytes: int = pipe.nbytes

        # Create a cuda stream and allocate Host memory
        device = vstream.device.name
        cuda = bool("cuda" in device)
        if cuda:
            cuda_stream: torch.cuda.Stream = torch.cuda.Stream(device)
            stream_context: StreamContext = torch.cuda.stream(cuda_stream)
            host_memories = [torch.empty(nbytes, dtype=torch.uint8, pin_memory=True) for _ in range(DEC_ENC_HOST_NBUFFERS)]
            views = [b.numpy() for b in host_memories]
            h2d_done: list[torch.cuda.Event | None] = [None] * DEC_ENC_HOST_NBUFFERS
            i = 0

            dlogger.debug(f"{f"[D] host memory:"} shape: {[pipe.shape]} dtype={pipe.dtype} nbytes={pipe.nbytes}")
        else:
            from contextlib import nullcontext
            stream_context = nullcontext()

        # Input stream
        in_shape: FShape = pipe.shape
        in_dtype: torch.dtype = pipe.dtype
        in_nbytes = pipe.nbytes

        # Image to tensor
        tensor_dtype = vstream.device.dtype
        # All input frames (from FFmpeg pipe) are already in RGB
        # flip_r_b: bool = bool(self.vpi.c_order != 'rgb')

        # Flow control
        remaining: int = self.media_stream.seek.count
        f_no: int = max(0, self.media_stream.seek.start)
        f_index: int = 0

        dlogger.debug(self.media_stream.seek)

        if verbose:
            print(lightcyan(f"[V][D] seek={self.media_stream.seek}"))
            print(lightcyan(
                f"[V][D] in_shape={in_shape}, in_dtype={in_dtype}, in_nbytes={in_nbytes}, remaining={remaining}"
            ))

        with stream_context:
            while (
                not self._stop_event.is_set()
                and remaining > 0
            ):
                if h2d_done[i] is not None:
                    h2d_done[i].synchronize()

                # ffmpeg write in host_memories
                n = d_stdout.readinto(views[i])
                if n < nbytes:
                    break

                d_img: Tensor = (
                    host_memories[i]
                    .to(device, non_blocking=True)
                    .view(in_dtype)
                    .view(in_shape)
                )
                d_tensor = img_to_tensor(d_img=d_img, tensor_dtype=tensor_dtype)

                # Create a frame object
                frame: NnFrame = NnFrame(
                    f_no=f_no,
                    tensor=d_tensor.clone(),
                    last=bool(remaining == 1),
                )
                mark_frame_ready(frame=frame, stream=cuda_stream)
                h2d_done[i] = frame.event

                if verbose:
                    print(
                        f"\n[V][D] ({lightcyan(f_index)}) ({f_no}), {remaining}. Tensor:",
                        f"{d_tensor.shape}, {d_tensor.dtype}, {d_tensor.data_ptr()}"
                    )

                # Send the frame to the consumer
                self.consumer.put_frame(frame)

                remaining -= 1
                f_index += 1
                f_no += 1
                i = (i + 1) % DEC_ENC_HOST_NBUFFERS

        if self.verbose:
            print(lightcyan(f"[V][D] End of decoding"))


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

