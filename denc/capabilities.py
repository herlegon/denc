import sys

from denc.vcodec import VideoCodec
import hsys
from hsys import (
    is_feature_supported,
    GpuDevices,

)

# Indicates if video codec is supported by the platform
# it uses the hsys package to determine if the codec is supported.


# Codecs that need a GPU
_NVENC_CODECS: list[VideoCodec] = [
    VideoCodec.H264_NVENC,
    VideoCodec.HEVC_NVENC,
    VideoCodec.AV1_NVENC,
]

_AMF_CODECS: list[VideoCodec] = [
    VideoCodec.H264_AMF,
    VideoCodec.HEVC_AMF,
]



def is_codec_supported(codec: VideoCodec) -> bool:
    gpu_devices = GpuDevices()
    if codec in _AMF_CODECS:
        return bool(gpu_devices.has_amd_gpu() and sys.platform == 'win32')

    if codec in _NVENC_CODECS:
        return bool(gpu_devices.has_intel_gpu())

    return True
