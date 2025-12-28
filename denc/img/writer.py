from concurrent.futures import ThreadPoolExecutor
from hytils import path_split, red
import multiprocessing
import os
from queue import Queue
from threading import Thread
import numpy as np
import torch
from torch import Tensor
from torch.cuda import StreamContext

from .io import write_image
from ..torch_tensor import tensor_to_img
from ..dh_transfers import dtoh_transfer



def _write_cuda_tensors(
    filepaths: list[str],
    tensors: list[Tensor],
) -> None:

    # Create a cuda stream and allocate Host memory
    device = tensors[0].device
    cuda_stream: torch.cuda.Stream = torch.cuda.Stream(device)
    stream_context: StreamContext = torch.cuda.stream(cuda_stream)

    nbytes: int = 0
    host_mem: Tensor = torch.empty(1, dtype=torch.uint8)

    def _write_img_thread(queue: Queue):
        filepath: str
        img: np.ndarray
        while True:
            # Wait for a frame or a poison pill
            fp_img = queue.get(block=True)
            if fp_img is None:
                break

            filepath, img = fp_img
            out_dir: str = path_split(filepaths[0])[0]
            os.makedirs(out_dir, exist_ok=True)
            write_image(filepath=filepath, img=img)


    _queue: Queue = Queue(maxsize=2)
    _thread = Thread(target=_write_img_thread, args=(_queue))
    _thread.start()

    with stream_context:
        for filepath, d_tensor in zip(filepaths, tensors):
            d_img: Tensor = tensor_to_img(
                tensor=d_tensor, img_dtype=torch.uint8, flip_r_b=True
            )

            # Allocate a new host mem if size differs
            h_img_nbytes: int = d_img.numel() * d_img.element_size()
            if h_img_nbytes != nbytes:
                del host_mem
                host_mem: Tensor = torch.empty(nbytes, dtype=torch.uint8, pin_memory=True)

            out_img: np.ndarray = dtoh_transfer(
                host_mem=host_mem,
                d_img=d_img,
                cuda_stream=cuda_stream
            )
            _queue.put((filepath, out_img))

    _queue.put(None)
    _thread.join()



def write_images(
    filepaths: list[str],
    images: list[np.ndarray | Tensor],
) -> None:

    # All frames must be on the same device
    device = ""
    error: bool = False
    for img in images:
        if isinstance(img, Tensor):
            if not device:
                device = img.device
            elif img.device != device:
                error = True
                break
        elif device:
            error = True
            break
    if error:
        raise ValueError(red(f"All images must be on the same device: {device if device else 'cpu'}"))

    # Use a specific functions for tensors in a cuda device
    img0: np.ndarray | Tensor = images[0]
    if isinstance(img0, Tensor) and "cuda" in img0.device.type:
        _write_cuda_tensors(filepaths, tensors=images)
        return

    # Consider all images in cpu
    def _write_img_or_tensor(filepath: str, img: np.ndarray | Tensor):
        out_dir: str = path_split(filepaths[0])[0]
        os.makedirs(out_dir, exist_ok=True)
        write_image(
            filepath=filepath,
            img=(
                tensor_to_img(tensor=img, img_dtype=np.uint8, flip_r_b=True).numpy()
                if isinstance(img, Tensor)
                else img
            )
        )

    cpu_count = min(
        int(multiprocessing.cpu_count() * 3 / 4),
        multiprocessing.cpu_count() - 2
    )
    with ThreadPoolExecutor(max_workers=cpu_count) as executor:
        executor.map(_write_img_or_tensor, filepaths, images)

