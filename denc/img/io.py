from concurrent.futures import ThreadPoolExecutor
import cv2
import glob
from hytils import absolute_path, path_split
import multiprocessing
import numpy as np
import os
from pathlib import Path
from pprint import pprint
from typing import Literal
import torch
from torch import Tensor

from ..utils.np_dtypes import (
    np_to_float32,
    np_to_uint8,
)
from ..torch_tensor import (
    img_to_tensor,
    tensor_to_img,
)


CPU_COUNT: int = multiprocessing.cpu_count() - 1


def img_info(img: np.ndarray | torch.Tensor) -> str:
    if isinstance(img, torch.Tensor):
        return f"{img.shape}, {img.dtype}, {img.device}, [{torch.min(img):.03f} .. {torch.max(img):.03f}]"

    if len(img.shape) < 2:
        w = 1
        h = img.shape[0]
    else:
        h, w = img.shape[:2]
    range_str: str = f"[{np.min(img):.03f} .. {np.max(img):.03f}]"
    return f"{w}x{h}, {img.dtype}, {range_str}"


def load_image(filepath: Path, dtype: np.dtype = np.uint8) -> np.ndarray:
    """Load an image
    """
    img: np.ndarray = cv2.imdecode(
            np.fromfile(filepath, dtype=np.uint8),
            cv2.IMREAD_UNCHANGED
        )
    return img if dtype == np.uint8 else np_to_float32(img)


def load_image_fp32(filepath: Path) -> np.ndarray:
    return np_to_float32(
        cv2.imdecode(
            np.fromfile(filepath, dtype=np.uint8),
            cv2.IMREAD_UNCHANGED
        )
    )


def write_image(filepath: Path, img: np.ndarray) -> None:
    # Support uint8 only as these functions aare used for debugging purpose
    # no nedd to improve this
    out_dir, _, extension = path_split(filepath)
    os.makedirs(out_dir, exist_ok=True)
    try:
        _, img_buffer = cv2.imencode(f".{extension}",np_to_uint8(img))
        with open(filepath, "wb") as buffered_writer:
            buffered_writer.write(img_buffer)
    except Exception as e:
        raise RuntimeError(f"Failed to save image as {filepath}, reason: {type(e)}")


def load_images(
    filepaths: list[Path],
    dtype: np.dtype = Literal[np.uint8, np.float32],
    cpu_count: int = 4,
) -> list[np.ndarray]:
    """Load images as BGR numpy array
    """
    imgs: list[np.ndarray] = []
    load_img_function = load_image_fp32 if dtype == np.float32 else load_image
    if len(filepaths) == 1:
        imgs = [load_img_function(filepaths[0])]

    with ThreadPoolExecutor(max_workers=min(CPU_COUNT, cpu_count)) as executor:
        for img in executor.map(load_img_function, filepaths):
            imgs.append(img)
    return imgs



def write_images(
    filepaths: list[str],
    images: tuple[np.ndarray],
    cpu_count: int = 4,
) -> None:
    """Write BGR images
    """
    if len(filepaths) == 1 or len(images) == 1:
        write_image(filepath=filepaths[0], img=images[0])
    else:
        with ThreadPoolExecutor(
            max_workers=min(CPU_COUNT, cpu_count, len(filepaths), len(images))
        ) as executor:
            executor.map(write_image, filepaths, images)


def get_image_list(directory: str | Path, extension: str = '.png') -> list[str]:
    directory = os.path.normpath(
        os.path.realpath(absolute_path(str(directory)))
    )
    # fastest for simple filtering
    return [
        os.path.join(directory, f)
        for f in sorted(os.listdir(directory)) if f.endswith(extension)
    ]

    # +50%
    files: list[str] = glob.glob(
        f"*{extension}",
        root_dir=directory,
        dir_fd=None,
        recursive=False,
        include_hidden=False
    )
    return [os.path.join(directory, f) for f in sorted(files)]


def write_tensor(
    filepath: str,
    d_tensor: torch.Tensor,
    norm: bool = False,
    flip_r_b: bool = True,
) -> None:
    """ Save a 4D tensor as an image". SYnchronous operation. Slow
    """
    if norm:
        min_value, max_value = torch.min(d_tensor), torch.max(d_tensor)
        if min_value < 0 or max_value > 1:
            d_tensor = (d_tensor - min_value)  / (max_value - min_value)

    d_img: Tensor = tensor_to_img(
        tensor=d_tensor,
        img_dtype=np.uint8,
        flip_r_b=flip_r_b,
    )
    h_img: np.ndarray = d_img.detach().cpu().numpy()
    write_image(filepath, h_img)



def load_image_as_tensor(
    filepath: Path,
    dtype: torch.dtype = torch.float32
) -> Tensor:
    img: np.ndarray = cv2.imdecode(
        np.fromfile(filepath, dtype=np.uint8),
        cv2.IMREAD_UNCHANGED
    )
    h_img: Tensor = img_to_tensor(
        torch.from_numpy(img),
        tensor_dtype=dtype,
        flip_r_b=True,
    )
    return h_img
