from enum import Enum
from .vcodec import VideoCodec


DEFAULT_H265_FFMPEG_ARGS: str = """
    -preset slow
    -crf 16
    -profile:v main422-10
    -x265-params sao=0
"""

DEFAULT_HVEC_NVENC_FFMPEG_ARGS: str = """
    -profile:v main
    -b_ref_mode disabled
    -tag:v hvc1
    -g 30
    -preset p7
    -tune hq
    -rc constqp
    -qp 17
    -rc-lookahead 20
    -spatial_aq 1
    -aq-strength 15
    -b:v 0
"""

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



PRESET_CODECS = {
    VideoCodec.H264,        # libx264 : ultrafast ... veryslow
    VideoCodec.H265,        # libx265 : ultrafast ... veryslow
    VideoCodec.AV1,         # libsvtav1 : 0-13 (numérique, 0 = le plus lent)
    VideoCodec.H264_NVENC,  # p1-p7 (p1 = le plus rapide)
    VideoCodec.HEVC_NVENC,  # p1-p7
    VideoCodec.AV1_NVENC,   # p1-p7
}



def effective_preset(vcodec: VideoCodec, preset: X26xPreset) -> X26xPreset | None:
    """Preset really sent to ffmpeg, None if not applicable."""
    if (
        preset is not None
        and vcodec in VCODECS_PRESETS
        and preset in VCODECS_PRESETS[vcodec]
    ):
        return preset
    return None
