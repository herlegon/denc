from __future__ import annotations
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


vcodec_to_ffmpeg_vcodec: dict[VideoCodec, str] = {
    VideoCodec.H264: "libx264",
    VideoCodec.H265: "libx265",
    VideoCodec.VP9: "libvpx-vp9",
    VideoCodec.FFV1: "ffv1",
    VideoCodec.DNXHR: "dnxhd",
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


CUDA_DEVICE_OPTS = "-hwaccel cuda -hwaccel_output_format cuda"
VAAPI_DEVICE_OPTS = "-hwaccel vaapi -hwaccel_output_format vaapi -rc_mode CQP"
VULKAN_DEVICE_OPTS = "-init_hw_device vulkan=vkdev:0 -filter_hw_device vkdev -filter:v format=nv12,hwupload"
vcodec_opts: dict[VideoCodec, list[str]] = {
    # VideoCodec.H264_VULKAN: VULKAN_DEVICE_OPTS.split(" "),
    **{
        k: CUDA_DEVICE_OPTS.split()
        for k in [
            VideoCodec.H264_NVENC,
            VideoCodec.HEVC_NVENC,
            VideoCodec.AV1_NVENC
        ]
    },
    **{
        k: VAAPI_DEVICE_OPTS.split()
        for k in [
            VideoCodec.H264_VAAPI,
            VideoCodec.H265_VAAPI,
            VideoCodec.AV1_VAAPI,
            VideoCodec.VP9_VAAPI
        ]
    },
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
    VideoCodec.PRORES: ".mov",
    VideoCodec.AV1: ".mp4",

    # VideoCodec.H264_VULKAN: ".mkv",

    VideoCodec.H264_NVENC: ".mkv",
    VideoCodec.HEVC_NVENC: ".mkv",
    VideoCodec.AV1_NVENC: ".mp4",

    VideoCodec.H264_VAAPI: ".mkv",
    VideoCodec.H265_VAAPI: ".mkv",
    VideoCodec.AV1_VAAPI: ".mp4",
    VideoCodec.VP9_VAAPI: "vp9_vaapi",

    VideoCodec.H264_AMF: ".mkv",
    VideoCodec.HEVC_AMF: ".mkv",
}


supported_pixfmt: dict[VideoCodec, tuple[PixFmt]] = {
    VideoCodec.H264: (PixFmt.YUV420P,),
    VideoCodec.H265: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.YUV444P10),
    VideoCodec.FFV1: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.RGB24, PixFmt.RGB48),
    VideoCodec.DNXHR: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.YUV444P10),
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
    VideoCodec.PRORES: CodecProfile(
        available=("proxy", "lt", "standard", "hq", "4444", "4444xq"),
        default=str(ProResProfile.Standard)
    ),

    # VideoCodec.H264_VULKAN: CodecProfile(available=(), default=""),
    VideoCodec.H264_VAAPI: CodecProfile(available=(), default=""),

}


