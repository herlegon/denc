from .vcodec import VideoCodec


# (min, max, default)
CRF_RANGES: dict[VideoCodec, tuple[int, int, int]] = {
    VideoCodec.H264: (0, 51, 23),
    VideoCodec.H265: (0, 51, 28),
    VideoCodec.VP9:  (0, 63, 31),   # nécessite aussi -b:v 0
    VideoCodec.AV1:  (0, 63, 35),   # libsvtav1
}


VCODECS_WITH_CRF = {
    VideoCodec.H264,   # libx264 : 0-51
    VideoCodec.H265,   # libx265 : 0-51
    VideoCodec.VP9,    # libvpx-vp9 : 0-63, à combiner avec -b:v 0
    VideoCodec.AV1,    # libsvtav1 : 0-63
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


def effective_crf(vcodec: VideoCodec, crf: int) -> int | None:
    """CRF really sent to ffmpeg (clamped), None if the codec has no CRF."""
    if vcodec not in CRF_RANGES:
        return None
    lo, hi = CRF_RANGES[vcodec][:2]
    return max(lo, min(crf, hi))


