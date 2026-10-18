from typing import Literal, TypeAlias, get_args


ContainerFormat: TypeAlias = Literal[
    '.mp4',     # H.264, H.265, MPEG-4
    '.mkv',     # H.264, H.265, VP9, FFV1
    '.mov',     # ProRes, H.264, H.265 (QuickTime)
    '.avi',     # DivX, Xvid, MJPEG
    '.mxf',     # DNxHR, AVC-Intra
    '.webm',    # VP8, VP9 (WebM container)
]

SUPPORTED_CONTAINER_FORMATS = list(get_args(ContainerFormat))

