from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
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
    VideoCodec.AV1: (PixFmt.YUV420P, PixFmt.YUV420P10, PixFmt.YUV422P10),

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



