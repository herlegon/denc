from datetime import (
    datetime,
    timedelta,
)
from fractions import Fraction
import math
from typing import TypeAlias


FrameRate: TypeAlias = Fraction


def frame_to_s(no: int, frame_rate: FrameRate) -> float:
    return float(no * frame_rate.denominator) / float(frame_rate.numerator)


def frame_to_ms(no: int, frame_rate: FrameRate) -> float:
    return 1000. * frame_to_s(no, frame_rate)


def frame_to_sexagesimal(no: int, frame_rate: FrameRate) -> str:
    """This function returns an approximate segaxesimal value.
        the ms are rounded to the near integer value.
        FFmpeg '-ss' option uses rounded ms
    """
    s: float = (float(no * frame_rate.denominator)) / float(frame_rate.numerator)
    print(s)
    frac, s = math.modf(s)
    return f"{timedelta(seconds=int(s))}.{int(1000 * frac):03}"


def ms_to_frame(ms: float, frame_rate: FrameRate) -> int:
    return int((ms * frame_rate.numerator) / (1000. * frame_rate.denominator))


def sexagesimal_to_frame(hms: str, frame_rate: FrameRate) -> int:
    h_m_s = hms.split(':')
    h_m_s_len: int = len(h_m_s)
    if not hms or not 1 <= h_m_s_len <= 3:
        raise ValueError(f"[{hms}] is not valid sexagesimal value")
    h, m, s = 0., 0., float(h_m_s[-1])
    m: float = float(h_m_s[-2]) if h_m_s_len > 1 else 0.
    h: float = float(h_m_s[-3]) if h_m_s_len > 2 else 0.
    ms: int = int(1000 * (h * 3600 + m * 60 + s))
    return ms_to_frame(ms, frame_rate)


def s_to_sexagesimal(s: float) -> str:
    frac, s = math.modf(s)
    return f"{timedelta(seconds=int(s))}.{int(1000 * frac):03}"


def current_datetime_str() -> str:
    return datetime.now().strftime(r"%Y-%m-%d %H:%M:%S")


def reformat_datetime(date_str: str) -> str | None:
    """Returns the datetime to a string which can be used as a filename"""
    date_format = "%a, %d %b %Y %H:%M:%S GMT"
    try:
        d = datetime.strptime(date_str, date_format)
    except:
        d_str: str = date_str
        for c in (' ', ',', ':', ','):
            d_str = d_str.replace(c, '_')
        return d_str
    return d.strftime("%Y-%m-%d_%H-%M-%S")
