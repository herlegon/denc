from __future__ import annotations
import functools
import os
import sys
from pathlib import Path
from dataclasses import dataclass
from enum import Enum, IntEnum
from .pxl_fmt import PixFmt


supported_video_exts: tuple[str, ...] = (
    '.mp4',     # H.264, H.265, MPEG-4
    '.mkv',     # H.264, H.265, VP9, FFV1
    '.mov',     # ProRes, H.264, H.265 (QuickTime)
    '.avi',     # DivX, Xvid, MJPEG
    '.mxf',     # DNxHR, AVC-Intra
    '.webm',    # VP8, VP9 (WebM container)
    '.flv',     # H.264, Sorenson Spark
    '.ts',      # H.264/H.265 (MPEG-TS streaming)
    '.ogg',     # Theora (less common)
    '.wmv',     # WMV codecs (Windows Media)
    '.3gp',     # H.263/H.264 (mobile devices)
)


class PatternName(Enum):
    SMPTEHDBARS = "smptehdbars"
    YUVTESTSRC = "yuvtestsrc"
    COLORCHART = "colorchart"


pretty_pattern_name: dict[PatternName, str] = {
    PatternName.SMPTEHDBARS: "smpte",
    PatternName.YUVTESTSRC: "yuv",
    PatternName.COLORCHART: "cchart",
}


class VideoCodec(Enum):
    H264 = "h264"
    H265 = "h265"
    FFV1 = "FFv1"
    DNXHR = "DNxHR"
    AV1 = "av1"
    VP9 = "VP9"
    PRORES = "ProRes"

    H264_NVENC = "h264_nvenc"
    HEVC_NVENC = "hevc_nvenc"
    AV1_NVENC = "av1_nvenc"

    H264_AMF = "h264_amf"
    HEVC_AMF = "hevc_amf"

    @classmethod
    def _missing_(cls, value):
        if isinstance(value, str):
            value_lower = value.lower()

            for member in cls:
                if member.value.lower() == value_lower:
                    return member

        return None


vcodec_to_ffmpeg_vcodec: dict[VideoCodec, str] = {
    VideoCodec.H264: "libx264",
    VideoCodec.H265: "libx265",
    VideoCodec.VP9: "libvpx-vp9",
    VideoCodec.FFV1: "ffv1",
    VideoCodec.DNXHR: "dnxhd",
    VideoCodec.PRORES: "prores_ks",
    VideoCodec.AV1: "libsvtav1",

    VideoCodec.H264_NVENC: "h264_nvenc",
    VideoCodec.HEVC_NVENC: "hevc_nvenc",
    VideoCodec.AV1_NVENC: "av1_nvenc",

    VideoCodec.H264_AMF: "h264_amf",
    VideoCodec.HEVC_AMF: "hevc_amf",
}




# Platform-dependent FFmpeg options for hardware codecs:
# - Input options (BEFORE -i): e.g. -vaapi_device on Linux
#   Note: rawvideo pipe inputs do NOT use -hwaccel cuda (decoder option).
# Output options (AFTER -i, applying to the encoder/output)
vcodec_output_opts: dict[VideoCodec, list[str]] = {}


# if IS_WINDOWS:
#     # Windows: AMD AMF (native on Windows for AMD Radeon GPUs)
#     for k in _AMF_CODECS:
#         vcodec_output_opts[k] = ["-rc", "cqp"]

# Legacy alias
vcodec_opts: dict[VideoCodec, list[str]] = {
    **vcodec_output_opts,
}



vcodec_to_extension: dict[VideoCodec, str] = {
    VideoCodec.H264: ".mkv",
    VideoCodec.H265: ".mkv",
    VideoCodec.H265: ".mkv",
    VideoCodec.VP9: ".webm",
    VideoCodec.FFV1: ".mkv",
    VideoCodec.DNXHR: ".mxf",
    VideoCodec.PRORES: ".mov",
    VideoCodec.AV1: ".mp4",

    VideoCodec.H264_NVENC: ".mkv",
    VideoCodec.HEVC_NVENC: ".mkv",
    VideoCodec.AV1_NVENC: ".mp4",

    VideoCodec.H264_AMF: ".mkv",
    VideoCodec.HEVC_AMF: ".mkv",
}


VCODEC_PIXFMTS: dict[VideoCodec, tuple[PixFmt, ...]] = {
    VideoCodec.H264: (PixFmt.YUV420P,),
    VideoCodec.H265: (
        PixFmt.YUV420P,
        PixFmt.YUV420P10,
        PixFmt.YUV422P,
        PixFmt.YUV422P10,
        PixFmt.YUV444P,
        PixFmt.YUV444P10
    ),
    VideoCodec.FFV1: (
        PixFmt.YUV420P,
        PixFmt.YUV420P10,
        PixFmt.YUV422P,
        PixFmt.YUV422P10,
        PixFmt.YUV444P,
        PixFmt.YUV444P10,
        PixFmt.RGB24,
        PixFmt.RGB48
    ),
    VideoCodec.DNXHR: (
        PixFmt.YUV422P,
        PixFmt.YUV422P10,
        PixFmt.YUV444P10,
    ),
    VideoCodec.PRORES: (PixFmt.YUV422P10, PixFmt.YUV444P10),
    VideoCodec.VP9: (
        PixFmt.YUV420P,
        PixFmt.YUV420P10,
        PixFmt.YUV420P12,
        PixFmt.YUV422P,
        PixFmt.YUV422P10,
        PixFmt.YUV422P12,
    ),
    VideoCodec.AV1: (PixFmt.YUV420P, PixFmt.YUV420P10),

    VideoCodec.H264_NVENC: (PixFmt.YUV420P,),
    VideoCodec.HEVC_NVENC: (PixFmt.YUV420P, PixFmt.YUV420P10),
    VideoCodec.AV1_NVENC: (PixFmt.YUV420P, PixFmt.YUV420P10),

    VideoCodec.H264_AMF: (PixFmt.YUV420P,),
    VideoCodec.HEVC_AMF: (PixFmt.YUV420P, PixFmt.YUV422P10),
}


PIXFMT_TO_FFMPEG: dict[PixFmt, str] = {
    PixFmt.YUV420P:     "yuv420p",
    PixFmt.YUV420P10:   "yuv420p10le",
    PixFmt.YUV420P12:   "yuv420p12le",
    PixFmt.YUV422P:     "yuv422p",
    PixFmt.YUV422P10:   "yuv422p10le",
    PixFmt.YUV422P12:   "yuv422p12le",
    PixFmt.YUV444P:     "yuv444p",
    PixFmt.YUV444P10:   "yuv444p10le",
    PixFmt.RGB24:       "bgr0",       # FFV1
    PixFmt.RGB48:       "gbrp16le",   # FFV1
    PixFmt.RGBA24:      "rgba24",
    PixFmt.RGBA48:      "rgba48le",
}


# Hardware codecs
VCODEC_PIXFMT_OVERRIDES: dict[VideoCodec, dict[PixFmt, str]] = {
    VideoCodec.H264_NVENC: {PixFmt.YUV420P: "nv12"},
    VideoCodec.HEVC_NVENC: {PixFmt.YUV420P: "nv12", PixFmt.YUV420P10: "p010le"},
    VideoCodec.AV1_NVENC:  {PixFmt.YUV420P: "nv12", PixFmt.YUV420P10: "p010le"},
    VideoCodec.H264_AMF:   {PixFmt.YUV420P: "nv12"},
    VideoCodec.HEVC_AMF:   {PixFmt.YUV420P: "nv12", PixFmt.YUV420P10: "p010le"},
}


def to_ffmpeg_pixfmt(vcodec: VideoCodec, pixfmt: PixFmt) -> str:
    if pixfmt not in VCODEC_PIXFMTS[vcodec]:
        raise ValueError(
            f"{pixfmt.name} not supported by {vcodec.name}, "
            f"values: {[p.name for p in VCODEC_PIXFMTS[vcodec]]}"
        )
    return VCODEC_PIXFMT_OVERRIDES.get(vcodec, {}).get(pixfmt, PIXFMT_TO_FFMPEG[pixfmt])



CRF_CODECS = {
    VideoCodec.H264,   # libx264 : 0-51
    VideoCodec.H265,   # libx265 : 0-51
    VideoCodec.VP9,    # libvpx-vp9 : 0-63, à combiner avec -b:v 0
    VideoCodec.AV1,    # libsvtav1 : 0-63
}


def effective_crf(vcodec: VideoCodec, crf: int) -> int | None:
    """CRF really sent to ffmpeg (clamped), None if the codec has no CRF."""
    if vcodec not in CRF_RANGES:
        return None
    lo, hi = CRF_RANGES[vcodec][:2]
    return max(lo, min(crf, hi))



PRESET_CODECS = {
    VideoCodec.H264,        # libx264 : ultrafast ... veryslow
    VideoCodec.H265,        # libx265 : ultrafast ... veryslow
    VideoCodec.AV1,         # libsvtav1 : 0-13 (numérique, 0 = le plus lent)
    VideoCodec.H264_NVENC,  # p1-p7 (p1 = le plus rapide)
    VideoCodec.HEVC_NVENC,  # p1-p7
    VideoCodec.AV1_NVENC,   # p1-p7
}


# presets
class X26xPreset(str, Enum):
    ULTRAFAST = "ultrafast"
    SUPERFAST = "superfast"
    VERYFAST = "veryfast"
    FASTER = "faster"
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"
    SLOWER = "slower"
    VERYSLOW = "veryslow"
    PLACEBO = "placebo"
X26X_PRESETS = [preset for preset in X26xPreset]




# (min, max, default)
CRF_RANGES: dict[VideoCodec, tuple[int, int, int]] = {
    VideoCodec.H264: (0, 51, 23),
    VideoCodec.H265: (0, 51, 28),
    VideoCodec.VP9:  (0, 63, 31),   # nécessite aussi -b:v 0
    VideoCodec.AV1:  (0, 63, 35),   # libsvtav1
}

# valeurs autorisées, de la plus rapide à la plus lente
# (sauf AV1 : 0 = la plus lente, 13 = la plus rapide)
VCODECS_PRESETS: dict[VideoCodec, list[str]] = {
    VideoCodec.H264: X26X_PRESETS,
    VideoCodec.H265: X26X_PRESETS,
    VideoCodec.AV1: [str(i) for i in range(0, 14)],   # 0-13
    VideoCodec.H264_NVENC: [f"p{i}" for i in range(1, 8)],   # p1 (rapide) - p7 (lent)
    VideoCodec.HEVC_NVENC: [f"p{i}" for i in range(1, 8)],
    VideoCodec.AV1_NVENC: [f"p{i}" for i in range(1, 8)],
}



VCODECS_WITHOUT_CRF = (
    VideoCodec.DNXHR,
    VideoCodec.PRORES,
    VideoCodec.H264_NVENC,
    VideoCodec.HEVC_NVENC,
    VideoCodec.AV1_NVENC,
    VideoCodec.H264_AMF,
    VideoCodec.HEVC_AMF,
)

VCODECS_WITH_CRF = {
    VideoCodec.H264,
    VideoCodec.H265,
    VideoCodec.AV1,
    VideoCodec.VP9,
}



VCODECS_WITHOUT_PRESET = (
    VideoCodec.AV1,
    VideoCodec.VP9,
    VideoCodec.PRORES,
    VideoCodec.H264_NVENC,
    VideoCodec.HEVC_NVENC,
    VideoCodec.AV1_NVENC,
    VideoCodec.H264_AMF,
    VideoCodec.HEVC_AMF,
)


@dataclass(slots=True)
class Ffv1CodecOption:
    level: int | None = None
    coder: int | None = None
    context: int | None = None
    g: int | None = None
    slices: int | None = None
    slicecrc: int | None = None

    def to_arg_list(self) -> list[str]:
        args: list[str] = []
        if self.level:
            args.extend(["-level", self.level])
        if self.coder:
            args.extend(["-coder", self.coder])
        if self.context:
            args.extend(["-context", self.context])
        if self.g:
            args.extend(["-g", self.g])
        if self.slices:
            args.extend(["-slices", self.slices])
        if self.slicecrc:
            args.extend(["-slicecrc", self.slicecrc])

        return args



