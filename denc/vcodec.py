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
    '.mxf',     # DNxHD, DNxHR, AVC-Intra
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
    DNXHD = "DNxHD"
    AV1 = "av1"
    VP9 = "VP9"
    PRORES = "ProRes"

    # H264_VULKAN = "h264_vulkan"

    H264_NVENC = "h264_nvenc"
    HEVC_NVENC = "hevc_nvenc"
    AV1_NVENC = "av1_nvenc"

    H264_VAAPI = "h264_vaapi"
    H265_VAAPI = "h265_vaapi"
    AV1_VAAPI = "av1_vaapi"
    VP9_VAAPI = "vp9_vaapi"

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
    VideoCodec.DNXHD: "dnxhd",
    VideoCodec.PRORES: "prores_ks",
    VideoCodec.AV1: "libsvtav1",

    # VideoCodec.H264_VULKAN: "h264_vulkan",

    VideoCodec.H264_NVENC: "h264_nvenc",
    VideoCodec.HEVC_NVENC: "hevc_nvenc",
    VideoCodec.AV1_NVENC: "av1_nvenc",

    VideoCodec.H264_VAAPI: "h264_vaapi",
    VideoCodec.H265_VAAPI: "h265_vaapi",
    VideoCodec.AV1_VAAPI: "av1_vaapi",
    VideoCodec.VP9_VAAPI: "vp9_vaapi",

    VideoCodec.H264_AMF: "h264_amf",
    VideoCodec.HEVC_AMF: "hevc_amf",
}


IS_LINUX: bool = sys.platform == "linux"
IS_WINDOWS: bool = sys.platform == "win32"

# Codec vendor / platform classifications
_VAAPI_CODECS: list[VideoCodec] = [
    VideoCodec.H264_VAAPI,
    VideoCodec.H265_VAAPI,
    VideoCodec.AV1_VAAPI,
    VideoCodec.VP9_VAAPI,
]

_NVENC_CODECS: list[VideoCodec] = [
    VideoCodec.H264_NVENC,
    VideoCodec.HEVC_NVENC,
    VideoCodec.AV1_NVENC,
]

_AMF_CODECS: list[VideoCodec] = [
    VideoCodec.H264_AMF,
    VideoCodec.HEVC_AMF,
]


def is_vaapi_codec(codec: VideoCodec) -> bool:
    """Return True if codec is VAAPI-based (Linux only)."""
    return codec in _VAAPI_CODECS


def is_nvenc_codec(codec: VideoCodec) -> bool:
    """Return True if codec is NVIDIA NVENC (Windows and Linux)."""
    return codec in _NVENC_CODECS


def is_amf_codec(codec: VideoCodec) -> bool:
    """Return True if codec is AMD AMF (Windows native)."""
    return codec in _AMF_CODECS


def is_hwaccel_codec(codec: VideoCodec) -> bool:
    """Return True if codec uses hardware acceleration."""
    return is_vaapi_codec(codec) or is_nvenc_codec(codec) or is_amf_codec(codec)


def get_vaapi_device() -> str:
    """Find the default VAAPI render device on Linux."""
    if not IS_LINUX:
        return ""
    for i in range(128, 136):
        dev = f"/dev/dri/renderD{i}"
        if os.path.exists(dev):
            return dev
    if os.path.exists("/dev/dri/card0"):
        return "/dev/dri/card0"
    return "/dev/dri/renderD128"


def codec_platform_check(codec: VideoCodec, platform: str = sys.platform) -> tuple[bool, str]:
    """Check whether a codec is supported on the given operating system."""
    if platform == "win32" and is_vaapi_codec(codec):
        return False, (
            f"VAAPI codec '{codec.value}' is only available on Linux (Intel/AMD). "
            f"On Windows, use AMF for AMD ({VideoCodec.H264_AMF.value}, {VideoCodec.HEVC_AMF.value}) "
            f"or NVENC for NVIDIA ({VideoCodec.H264_NVENC.value}, {VideoCodec.HEVC_NVENC.value})."
        )
    if platform == "linux" and is_amf_codec(codec):
        return False, (
            f"AMF codec '{codec.value}' is only supported on Windows for AMD GPUs."
        )
    return True, ""


@functools.lru_cache(maxsize=None)
def is_codec_supported(codec: VideoCodec, check_hardware: bool = True) -> bool:
    """Return True if codec is supported on the current platform and hardware."""
    valid, _ = codec_platform_check(codec)
    if not valid:
        return False

    if check_hardware and is_hwaccel_codec(codec):
        from .utils.tools import ffmpeg_exe
        import subprocess

        cmd = [
            ffmpeg_exe, "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=black:s=64x64:d=0.04",
        ]
        if is_vaapi_codec(codec):
            dev = get_vaapi_device()
            if not dev or not os.path.exists(dev):
                return False
            cmd.extend(["-vaapi_device", dev, "-vf", "format=nv12,hwupload"])
        cmd.extend(["-c:v", vcodec_to_ffmpeg_vcodec[codec], "-f", "null", "-y", "-"])
        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=3)
            return res.returncode == 0
        except Exception:
            return False

    return True


# Platform-dependent FFmpeg options for hardware codecs:
# - Input options (BEFORE -i): e.g. -vaapi_device on Linux
#   Note: rawvideo pipe inputs do NOT use -hwaccel cuda (decoder option).
# Output options (AFTER -i, applying to the encoder/output)
vcodec_output_opts: dict[VideoCodec, list[str]] = {}

if IS_LINUX:
    # Linux: VAAPI (Intel / AMD via Mesa/libva)
    vaapi_device: str = get_vaapi_device()
    vaapi_out = (["-vaapi_device", vaapi_device] if vaapi_device else []) + ["-rc_mode", "CQP"]

    for k in _VAAPI_CODECS:
        vcodec_output_opts[k] = list(vaapi_out)

    for k in _NVENC_CODECS + _AMF_CODECS:
        vcodec_output_opts[k] = []

elif IS_WINDOWS:
    for k in _VAAPI_CODECS + _NVENC_CODECS:
        vcodec_output_opts[k] = []

    # Windows: AMD AMF (native on Windows for AMD Radeon GPUs)
    for k in _AMF_CODECS:
        vcodec_output_opts[k] = ["-rc", "cqp"]

else:
    for k in _VAAPI_CODECS + _NVENC_CODECS + _AMF_CODECS:
        vcodec_output_opts[k] = []

# Legacy alias
vcodec_opts: dict[VideoCodec, list[str]] = {
    **vcodec_output_opts,
}


class ProResProfile(IntEnum):
    Proxy = 0
    LT = 1
    Standard = 2    # ProRes 422
    HQ = 3
    HQ_ALPHA = 4


# default profile
vcodec_default_profile: dict[VideoCodec, str] = {
    VideoCodec.H264: "",
    VideoCodec.H265: "",
    VideoCodec.VP9: "",
    VideoCodec.FFV1: "",
    VideoCodec.DNXHR: "dnxhr_hqx",
    VideoCodec.PRORES: str(ProResProfile.Standard),
}


vcodec_to_extension: dict[VideoCodec, str] = {
    VideoCodec.H264: ".mkv",
    VideoCodec.H265: ".mkv",
    VideoCodec.H265: ".mkv",
    VideoCodec.VP9: ".webm",
    VideoCodec.FFV1: ".mkv",
    VideoCodec.DNXHR: ".mxf",
    VideoCodec.DNXHD: ".mxf",
    VideoCodec.PRORES: ".mov",
    VideoCodec.AV1: ".mp4",

    # VideoCodec.H264_VULKAN: ".mkv",

    VideoCodec.H264_NVENC: ".mkv",
    VideoCodec.HEVC_NVENC: ".mkv",
    VideoCodec.AV1_NVENC: ".mp4",

    VideoCodec.H264_VAAPI: ".mkv",
    VideoCodec.H265_VAAPI: ".mkv",
    VideoCodec.AV1_VAAPI: ".mp4",
    VideoCodec.VP9_VAAPI: ".webm",

    VideoCodec.H264_AMF: ".mkv",
    VideoCodec.HEVC_AMF: ".mkv",
}


supported_pixfmt: dict[VideoCodec, tuple[PixFmt]] = {
    VideoCodec.H264: (PixFmt.YUV420P,),
    VideoCodec.H265: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.YUV444P10),
    VideoCodec.FFV1: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.RGB24, PixFmt.RGB48),
    VideoCodec.DNXHR: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.YUV444P10),
    VideoCodec.DNXHD: (PixFmt.YUV422P10,),
    VideoCodec.PRORES: (PixFmt.YUV422P10, PixFmt.YUV444P10),
    VideoCodec.VP9: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.YUV444P10),
    VideoCodec.AV1: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.YUV444P10),
}




@dataclass
class FFv1Settings:
    level: int = 1
    coder: int = 1
    context: int = 1
    g: int = 1
    threads: int = 8

@dataclass(slots=True)
class CodecProfile:
    available: tuple[str, ...]
    default: str


CODEC_PROFILE: dict[VideoCodec, CodecProfile] = {
    VideoCodec.H264: CodecProfile(
        available=("baseline", "main", "high", "high10", "high422", "high444"),
        default=""
    ),
    VideoCodec.H265: CodecProfile(
        available=("main", "main10", "mainstillpicture"), default=""
    ),
    VideoCodec.FFV1: CodecProfile(available=(), default=""),

    # mpeg2video    # "simple, main, high",
    # "No standard profiles exposed (VP8/VP9 use levels instead)"
    VideoCodec.VP9: CodecProfile(available=(), default=""),
    # libaom-av1    # "main, high, professional",
    VideoCodec.AV1: CodecProfile(
        available=("main", "high", "professional"), default="main"
    ),
    VideoCodec.H264_NVENC: CodecProfile(
        available=("baseline", "main", "high", "high444"), default=""
    ),
    VideoCodec.HEVC_NVENC: CodecProfile(available=("main", "main10", "rext"), default=""),
    VideoCodec.DNXHR: CodecProfile(
        available=("dnxhr_hqx", "lb", "sq", "hq", "hqx", "444"),
        default="dnxhr_hqx"
    ),
    VideoCodec.DNXHD: CodecProfile(
        available=("dnxhd",), default=""
    ),
    VideoCodec.AV1_NVENC: CodecProfile(
        available=("main", "high", "professional"), default=""
    ),
    VideoCodec.PRORES: CodecProfile(
        available=("proxy", "lt", "standard", "hq", "4444", "4444xq"),
        default=str(ProResProfile.Standard)
    ),

    # Hardware codecs
    VideoCodec.H264_VAAPI: CodecProfile(
        available=("constrained_baseline", "baseline", "main", "high"), default=""
    ),
    VideoCodec.H265_VAAPI: CodecProfile(available=("main", "main10"), default=""),
    VideoCodec.VP9_VAAPI: CodecProfile(available=("profile0", "profile1", "profile2", "profile3"), default=""),
    VideoCodec.AV1_VAAPI: CodecProfile(available=("main", "high", "professional"), default=""),

    VideoCodec.H264_AMF: CodecProfile(
        available=("constrained_baseline", "baseline", "main", "high"), default=""
    ),
    VideoCodec.HEVC_AMF: CodecProfile(available=("main", "main10"), default=""),
}


