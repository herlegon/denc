from .vcodec import VideoCodec


# Codec                    -tune    Valeurs
#-------------------------------------------------------
# H264 (libx264)            oui     film, animation, grain, stillimage, psnr, ssim, fastdecode, zerolatency
# H265 (libx265)            oui     psnr, ssim, grain, zerolatency, fastdecode, animation
# H264, HEVC, AV1 NVENC     oui     hq, ll, ull, lossless
# AV1 (libsvtav1)           non     passe par -svtav1-params tune=N, pas par -tune
# VP9, FFV1, DNxHR, ProRes  non     aucun
# H264_AMF, HEVC_AMF        non     AMF règle ça avec -usage et -quality, hors sujet ici


VCODEC_TUNES: dict[VideoCodec, tuple[str, ...]] = {
    VideoCodec.H264: (
        "film",
        "animation",
        "grain",
        "stillimage",
        "psnr",
        "ssim",
        "fastdecode",
        "zerolatency"
    ),
    VideoCodec.H265: (
        "psnr",
        "ssim",
        "grain",
        "zerolatency",
        "fastdecode",
        "animation"
    ),
    VideoCodec.H264_NVENC: ("hq", "ll", "ull", "lossless"),
    VideoCodec.HEVC_NVENC: ("hq", "ll", "ull", "lossless"),
    VideoCodec.AV1_NVENC:  ("hq", "ll", "ull", "lossless"),
}


def effective_tune(vcodec: VideoCodec, tune: str | None) -> str | None:
    """Tune really sent to ffmpeg, None if not applicable."""
    if (
        tune is not None
        and vcodec in VCODEC_TUNES
        and tune in VCODEC_TUNES[vcodec]
    ):
        return tune

    return None
