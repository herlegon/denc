from concurrent.futures import ThreadPoolExecutor
from hytils import red
import multiprocessing
from queue import Queue
from threading import Thread
import numpy as np
import torch
from torch import Tensor
from torch.cuda import StreamContext

from ..dh_transfers import htod_transfer
from .io import (
    load_image,
    load_images,
    load_image_as_tensor,
)
from ..torch_tensor import (
    Idtype,
    IdtypeToTorch,
    img_to_tensor,
    torch_dtype_to_np,
)


def _read_images_as_cuda_tensors(
    img_filepaths: list[str],
    device: str = "cuda:0",
    tensor_dtype: torch.dtype | Idtype = 'fp32',
) -> list[Tensor]:

    if not isinstance(tensor_dtype, torch.dtype):
        tensor_dtype = IdtypeToTorch[tensor_dtype]

    # CUDA: stream and host mem allocation
    cuda_stream: torch.cuda.Stream = torch.cuda.Stream(device)
    stream_context: StreamContext = torch.cuda.stream(cuda_stream)

    def _htod_transfer(
        queue: Queue,
        device: str,
        cuda_stream,
        tensors: list[Tensor],
    ):
        nbytes: int = 0
        host_mem: Tensor = torch.empty(1, dtype=torch.uint8)
        while True:
            h_img: Tensor = queue.get()
            if h_img is None:
                break

            # Allocate a new host mem if size differs
            h_img_nbytes: int = h_img.numel() * h_img.element_size()
            if h_img_nbytes != nbytes:
                del host_mem
                host_mem: Tensor = torch.empty(
                    nbytes, dtype=torch.uint8, pin_memory=True
                )

            # HtoD transfer
            d_img: Tensor = htod_transfer(
                host_mem=host_mem,
                img_buffer=h_img.contiguous().view(-1),
                img_dtype=h_img.dtype,
                img_shape=h_img.shape,
                cuda_stream=cuda_stream,
                device=device
            )

            # Image to 4D tensor
            d_tensor: Tensor = img_to_tensor(
                d_img=d_img, tensor_dtype=tensor_dtype, flip_r_b=True
            )
            tensors.append(d_tensor)


    tensors: list[Tensor] = []
    with stream_context:
        _queue: Queue = Queue(maxsize=2)
        _thread = Thread(
            target=_htod_transfer,
            args=(_queue, device, cuda_stream, tensors)
        )
        _thread.start()

        for img_fp in range(img_filepaths):
            _queue.put(torch.from_numpy(load_image(filepath=img_fp, dtype=np.uint8)))

        _queue.put(None)
        _thread.join()



def read_images(
    img_filepaths: list[str],
    dtype: torch.dtype | np.dtype = torch.float32,
    to_device: str = "cpu",
    as_tensor: bool = False,
    tensor_dtype: torch.dtype | Idtype = 'fp32',
) -> list[np.ndarray] | list[Tensor]:

    if "cuda" in to_device:
        if not torch.cuda.is_available():
            raise SystemError(red(f"No cuda device"))
        return _read_images_as_cuda_tensors(
            device=to_device,
            tensor_dtype=tensor_dtype,
        )
    elif to_device != 'cpu':
        raise ValueError(red(f"Not a valid device: {to_device}"))

    if not isinstance(tensor_dtype, torch.dtype):
        tensor_dtype = IdtypeToTorch[tensor_dtype]

    if as_tensor and tensor_dtype != torch.float32:
        raise ValueError(red(f"Cannot load frames in cpu with dtype={tensor_dtype}. Must be fp32 (torch.float32)"))

    in_imgs: list[np.ndarray] = []

    cpu_count = min(
        int(multiprocessing.cpu_count() * 3 / 4), multiprocessing.cpu_count() - 2
    )
    if not as_tensor:
        dtype: np.dtype = torch_dtype_to_np[dtype]
        in_imgs = load_images(img_filepaths, cpu_count=cpu_count, dtype=dtype)

    else:
        with ThreadPoolExecutor(max_workers=cpu_count) as executor:
            for in_img in executor.map(
                lambda args: load_image_as_tensor(*args),
                [(img_fp, tensor_dtype) for img_fp in img_filepaths]
            ):
                in_imgs.append(in_img)

    return in_imgs
