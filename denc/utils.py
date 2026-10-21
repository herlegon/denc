from dataclasses import fields, is_dataclass
from enum import Enum
from fractions import Fraction
from pathlib import Path

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



def tags(raw: dict[str, str | dict[str, str]]) -> dict[str, str]:
    """Tags ffprobe avec clés en minuscules (la casse varie selon le conteneur)."""
    return {
        k.lower(): v
        for k, v in raw.get("tags", {}).items()
    }



def _fmt(value) -> str:
    if isinstance(value, Enum):
        return value.name
    if isinstance(value, Fraction):
        if value.denominator == 1:
            return str(value.numerator)
        return f"{value.numerator}/{value.denominator} ({float(value):.3f})"
    if isinstance(value, torch.dtype):
        return str(value).removeprefix("torch.")
    if isinstance(value, Path):
        return str(value)
    return repr(value) if isinstance(value, str) else str(value)



def pretty(obj, indent: int = 0) -> str:
    """Multi-line, aligned representation of a (nested) dataclass.
    Fields declared with repr=False (e.g. `parent`) are skipped.
    Non-empty dicts are expanded, one item per line.
    Fields starting with '_' are listed last."""
    pad = "  " * indent
    sub = pad + "  "
    flds = [f for f in fields(obj) if f.repr]
    flds.sort(key=lambda f: f.name.startswith("_"))   # tri stable : False < True
    width = max((len(f.name) for f in flds), default=0)

    lines = [f"{pad}{type(obj).__name__}"] if indent == 0 else []
    for f in flds:
        value = getattr(obj, f.name)
        if is_dataclass(value):
            lines.append(f"{sub}{f.name}: {type(value).__name__}")
            lines.append(pretty(value, indent + 1))

        elif isinstance(value, dict) and value:
            lines.append(f"{sub}{f.name}:")
            kw = max(len(str(k)) for k in value)
            for k, v in value.items():
                lines.append(f"{sub}  {str(k):<{kw}} : {_fmt(v)}")

        else:
            lines.append(f"{sub}{f.name:<{width}} : {_fmt(value)}")

    return "\n".join(lines)

