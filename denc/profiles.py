
from enum import IntEnum

from hytils import red
from .pxl_fmt import PixFmt
from .vcodec import VideoCodec


VCODEC_PROFILES: dict[VideoCodec, tuple[str, ...]] = {
    VideoCodec.H264: ("baseline", "main", "high", "high444"),
    VideoCodec.H265: ("main", "main10", "main444-8", "main422-10", "main444-10"),
    # VideoCodec.FFV1: (),   # no profile (only -level 0/1/3)
    VideoCodec.DNXHR: ("dnxhr_lb", "dnxhr_sq", "dnxhr_hq", "dnxhr_hqx", "dnxhr_444"),
    VideoCodec.AV1: ("main", ),
    VideoCodec.VP9: ("0", "1", "2", "3"),
    VideoCodec.PRORES: ("proxy", "lt", "standard", "hq", "4444", "4444xq"),

    VideoCodec.H264_NVENC: ("baseline", "main", "high", "high444p"),
    VideoCodec.HEVC_NVENC: ("main", "main10"),
    VideoCodec.AV1_NVENC: ("main",),    # ffmpeg -h encoder=av1_nvenc

    VideoCodec.H264_AMF: ("constrained_baseline", "main", "high", "constrained_high"),
    VideoCodec.HEVC_AMF: ("main", "main10"),   # main10 on recent ffmpeg versions, not sure
}


H264_PROFILE_PIXFMT: dict[str, tuple[PixFmt, ...]] = {
    "baseline": (PixFmt.YUV420P,),
    "main":     (PixFmt.YUV420P,),
    "high":     (PixFmt.YUV420P,),
    "high444":  (PixFmt.YUV444P,),
}


H264_PROBE_TO_PROFILE_MAP: dict[str, str] = {
    "Constrained Baseline": 'baseline',
    "Main": 'main',
    "High": 'high',
    "High 4:4:4 Predictive": "high444",
    # "High 4:4:4 Predictive": "high444p",
}


H265_PROFILE_PIXFMT: dict[str, tuple[PixFmt, ...]] = {
    "main":       (PixFmt.YUV420P,),
    "main10":     (PixFmt.YUV420P10,),
    "main422-10": (PixFmt.YUV422P10,),
    "main444-8":  (PixFmt.YUV444P,),
    "main444-10": (PixFmt.YUV444P10,),
}

H265_PROBE_TO_PROFILE_MAP: dict[str, str] = {
    "Constrained Baseline": 'baseline',
    "Main": 'main',
    "Main 10": 'main10',
    "Rext": 'Rext',
}


DNXHR_PROFILE_PIXFMT: dict[str, tuple[PixFmt, ...]] = {
    "dnxhr_lb": (PixFmt.YUV422P,),
    "dnxhr_sq": (PixFmt.YUV422P,),
    "dnxhr_hq": (PixFmt.YUV422P,),
    "dnxhr_hqx": (PixFmt.YUV422P10,),
    "dnxhr_444": (PixFmt.YUV444P10,),
}


DNXHR_PROBE_TO_PROFILE_MAP: dict[str, str] = {
    "DNXHR LB": 'dnxhr_lb',
    "DNXHR SQ": 'dnxhr_sq',
    "DNXHR HQ": 'dnxhr_hq',
    "DNXHR HQX": 'dnxhr_hqx',
    "DNXHR 444": 'dnxhr_444',
}


AV1_PROFILE_PIXFMT: dict[str, tuple[PixFmt, ...]] = {
    "main": (PixFmt.YUV420P, PixFmt.YUV420P10),
}

AV1_PROBE_TO_PROFILE_MAP: dict[str, str] = {
    "Main": 'main',
}


VP9_PROFILE_PIXFMT: dict[str, tuple[PixFmt, ...]] = {
    "0": (PixFmt.YUV420P,),
    "1": (PixFmt.YUV422P,),
    "2": (PixFmt.YUV420P10, PixFmt.YUV420P12),
    "3": (PixFmt.YUV422P10, PixFmt.YUV422P12),
}

VP9_PROBE_TO_PROFILE_MAP: dict[str, str] = {
    'Profile 0': "0",
    'Profile 1': "1",
    'Profile 2': "2",
    'Profile 3': "3",
}


PRORES_PROFILE_PIXFMT: dict[str, tuple[PixFmt, ...]] = {
    "proxy":    (PixFmt.YUV422P10,),
    "lt":       (PixFmt.YUV422P10,),
    "standard": (PixFmt.YUV422P10,),
    "hq":       (PixFmt.YUV422P10,),
    "4444":     (PixFmt.YUVA444P12,),
    "4444xq":   (PixFmt.YUVA444P12,),
}


PRORES_PROBE_TO_PROFILE_MAP: dict[str, str] = {
    "Proxy": "proxy",
    "LT": "lt",
    "Standard": "standard",
    "HQ": "hq",
    "4444": "4444",
    "XQ": "4444xq",
}


H264_NVENC_PROBE_TO_PROFILE_MAP: dict[str, str] = {
    "Constrained Baseline": 'baseline',
    "Main": 'main',
    "High": 'high',
    "High 4:4:4 Predictive": "high444p",
}



PROBE_TO_PROFILE_MAP: dict[str, str] = {
    VideoCodec.H264: H264_PROBE_TO_PROFILE_MAP,
    VideoCodec.H265: H265_PROBE_TO_PROFILE_MAP,
    VideoCodec.DNXHR: DNXHR_PROBE_TO_PROFILE_MAP,
    VideoCodec.AV1: AV1_PROBE_TO_PROFILE_MAP,
    VideoCodec.VP9: VP9_PROBE_TO_PROFILE_MAP,
    VideoCodec.PRORES: PRORES_PROBE_TO_PROFILE_MAP,
    VideoCodec.H264_NVENC: H264_NVENC_PROBE_TO_PROFILE_MAP,
}


VCODEC_PROFILE_PIXFMT: dict[VideoCodec, dict[str, tuple[PixFmt, ...]]] = {
    VideoCodec.H264: H264_PROFILE_PIXFMT,
    VideoCodec.H265: H265_PROFILE_PIXFMT,
    VideoCodec.DNXHR: DNXHR_PROFILE_PIXFMT,
    VideoCodec.AV1: AV1_PROFILE_PIXFMT,
    VideoCodec.AV1_NVENC: (),
    VideoCodec.VP9: VP9_PROFILE_PIXFMT,
    VideoCodec.PRORES: PRORES_PROFILE_PIXFMT,
    VideoCodec.H264_NVENC: H264_PROFILE_PIXFMT,
    VideoCodec.HEVC_NVENC: H265_PROFILE_PIXFMT,
}


# is (profile, pixfmt) allowed ?
def check_profile_pixfmt(vcodec: VideoCodec, profile: str, pixfmt: PixFmt):
    if vcodec == VideoCodec.DNXHR:
        expected = DNXHR_PROFILE_PIXFMT[profile][0]
        if pixfmt != expected:
            raise ValueError(f"H264 {profile} needs {expected.name}, got {pixfmt.name}")

    elif vcodec == VideoCodec.H264 and profile is not None:
        if profile is not None and pixfmt not in H264_PROFILE_PIXFMT[profile]:
            raise ValueError(f"H264 profile {profile} does not support {pixfmt.name}")

    elif vcodec == VideoCodec.H265 and profile is not None:
        if profile is not None and pixfmt not in H265_PROFILE_PIXFMT[profile]:
            raise ValueError(f"H265 profile {profile} does not support {pixfmt.name}")

    elif vcodec == VideoCodec.VP9:
        if profile is not None and pixfmt not in VP9_PROFILE_PIXFMT[profile]:
            raise ValueError(f"VP9 profile {profile} does not support {pixfmt.name}")

    elif vcodec == VideoCodec.AV1:
        if profile is not None and pixfmt not in AV1_PROFILE_PIXFMT[profile]:
            raise ValueError(f"AV1 profile {profile} does not support {pixfmt.name}")



def vp9_profile_for(pixfmt: PixFmt) -> str:
    for profile, pixfmts in VP9_PROFILE_PIXFMT.items():
        if pixfmt in pixfmts:
            return profile
    raise ValueError(f"No VP9 profile for {pixfmt.name}")



# DNxHR: pixfmt -> profiles ?
def dnxhr_profiles_for(pixfmt: PixFmt) -> str:
    profiles: list[str] = [p for p, pixfmts in DNXHR_PROFILE_PIXFMT.items() if pixfmt in pixfmts]
    if not profiles:
        raise ValueError(red(f"[DNxHR] Failed to find a valid profile for pixel formet {pixfmt.value}"))
    return profiles[-1]



# default profile
vcodec_default_pixfmt: dict[VideoCodec, str] = {
    VideoCodec.H264: H264_PROFILE_PIXFMT,
    VideoCodec.H265: H265_PROFILE_PIXFMT,
    VideoCodec.AV1: AV1_PROFILE_PIXFMT,
    VideoCodec.VP9: VP9_PROFILE_PIXFMT,
    VideoCodec.FFV1: PixFmt.RGB24,
    VideoCodec.DNXHR: DNXHR_PROFILE_PIXFMT,
    VideoCodec.PRORES: PRORES_PROFILE_PIXFMT,
}


def default_pixfmt_for_profile(vcodec: VideoCodec, profile: str | None) -> PixFmt:
    codec_profiles: PixFmt | dict = vcodec_default_pixfmt.get(vcodec, None)
    if codec_profiles is None or not profile:
        return (
            PixFmt.YUV422P10
            if vcodec in (VideoCodec.DNXHR, VideoCodec.PRORES)
            else PixFmt.YUV420P
        )

    if isinstance(codec_profiles, dict):
        if profile is None:
            raise ValueError(f"Missing profile for codec {vcodec.value}")

        pix_fmts: dict[str, PixFmt | tuple[PixFmt, ...]] = codec_profiles[profile]
        return pix_fmts[0] if isinstance(pix_fmts, list | tuple) else pix_fmts

    else:
        return codec_profiles


DNXHR_DEFAULT_PROFILE: dict[PixFmt, str] = {
    PixFmt.YUV422P:   "dnxhr_hq",
    PixFmt.YUV422P10: "dnxhr_hqx",
    PixFmt.YUV444P10: "dnxhr_444",
}


def effective_profile(vcodec: VideoCodec, profile: str | None, pixfmt: PixFmt) -> str | None:
    """Profile really sent to ffmpeg, None if not applicable."""
    if vcodec == VideoCodec.DNXHR and profile is None:
        # without a dnxhr_* profile, ffmpeg falls back to classic DNxHD (fixed frame sizes only)
        return DNXHR_DEFAULT_PROFILE[pixfmt]

    if (
        vcodec in VCODEC_PROFILES
        and profile in VCODEC_PROFILES[vcodec]
        and vcodec != VideoCodec.AV1_NVENC
    ):
        return profile

    return None
