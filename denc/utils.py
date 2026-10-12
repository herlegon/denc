from fractions import Fraction

import numpy as np
import torch


def img_info(img: np.ndarray | torch.Tensor) -> str:
    if isinstance(img, torch.Tensor):
        return f"tensor: {img.shape}, {img.dtype}"

    h, w = img.shape[:2]
    range_str: str = f"[{np.min(img)} .. {np.max(img)}]"
    # range_str: str = (
    #     f"[{np.min(img)} .. {np.max(img)}]"
    #     if img.dtype in (np.uint8, np.uint16, np.uint32)
    #     else f"[{np.min(img):.02} .. {np.max(img):.02}]"
    # )
    return f"{w}x{h}, {img.dtype}, {range_str}"


def clean_str(line: str):
    cleaned: str = line
    for c in ('\\', '\"', ' ', '\r', '\n'):
        cleaned = cleaned.replace(c, '')
    return cleaned.strip()



def parse_fraction(value: str | None, default: str) -> Fraction:
    # ffprobe can return "N/A", "0/0" or "0:0" when the value is unknown
    if not value or value in ("0/0", "0:0", "N/A"):
        value = default

    try:
        return Fraction(value.replace(":", "/"))
    except (ValueError, ZeroDivisionError):
        return Fraction(default.replace(":", "/"))


