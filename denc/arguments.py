from argparse import ArgumentParser, ArgumentTypeError


class BoundedInteger:
    def __init__(self, min_value: int, max_value: int) -> None:
        self.min_value: int = min_value
        self.max_value: int = max_value

    def __call__(self, value) -> int:
        try:
            value = int(value)
        except:
            raise ArgumentTypeError(f"Value is not a valid argument.")
        if self.min_value <= value <= self.max_value:
            return value
        raise ArgumentTypeError(
            f"Value is not a valid argument, allowed range: {self.min_value}..{self.max_value}"
        )


class BoundedFloat:
    def __init__(self, min_value: float, max_value: float) -> None:
        self.min_value: float = min_value
        self.max_value: float = max_value

    def __call__(self, value) -> float:
        try:
            value = float(value)
        except:
            raise ArgumentTypeError(f"Value is not a valid argument.")
        if self.min_value <= value <= self.max_value:
            return value
        raise ArgumentTypeError(
            f"Value is not a valid argument, allowed range: {self.min_value}..{self.max_value}"
        )




def add_debug_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--debug",
        action="store_true",
        required=False,
        help="Enable verbose output for debugging."
    )



def add_io_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--input", "-i",
        type=str,
        default=f"in.mkv",
        required=False,
        help="Input video file."
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default="",
        required=False,
        help="Output video file. If empty, the name is generated from the input file name."
    )

    parser.add_argument(
        "--out_dir",
        type=str,
        default="",
        required=False,
        help="Output directory. If empty, the input file's directory is used."
    )

    parser.add_argument(
        "--append_params",
        action="store_true",
        required=False,
        help="Append the parameters to the output file name."
    )



def add_seek_arguments(parser: ArgumentParser) -> None:
#     parser.add_argument(
#         "-s",
#         "--strength",
#         type=BoundedInteger(1, 800),
#         metavar="[1..800]",
#         default=400,
#         required=False,
#         help="""Suppression strength of temporal inconsistencies.
# Higher means more aggressive.
# \n"""
#     )

    # Seeking
    parser.add_argument(
        "-ss",
        "--ss",
        type=str,
        required=False,
        default='',
        help="""Seeks in this input file to position.
HOURS:MM:SS.MILLISECONDS
Refer to https://ffmpeg.org//ffmpeg.html#Main-options
and https://ffmpeg.org//ffmpeg-utils.html#time-duration-syntax
\n"""
    )
    parser.add_argument(
        "-t",
        "--t",
        type=str,
        required=False,
        default='',
        help="""Limit the duration of data read from the input file.
HOURS:MM:SS.MILLISECONDS
Refer to https://ffmpeg.org//ffmpeg.html#Main-options
\n"""
    )
    parser.add_argument(
        "-to",
        "--to",
        type=str,
        required=False,
        default="",
        help="""Stop reading the input at position.
HOURS:MM:SS.MILLISECONDS
--to and --t are mutually exclusive and --t has priority.
Refer to https://ffmpeg.org//ffmpeg.html#Main-options"
\n"""
    )



def add_sar_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-fsar",
        "--fsar",
        type=str,
        default="",
        help="""SAR metadata may be not present in input video.
Use this one to resize the video and overwrite the one specified in metadata
Keep the height, modify the width.
It should normally never be used as it's really very specific.
format: 4/3 (or 16/9, etc.)
\n"""
    )

    parser.add_argument(
        "-fsar_h",
        "--fsar_h",
        type=str,
        default="",
        help="""SAR metadata may be not present in input video.
Use this one to resize the video and overwrite the one specified in metadata.
Keep the width, modify the height.
It should normally never be used as it's really very specific.
format: 4/3 (or 16/9, etc.)
\n"""
    )



def add_ffmpeg_arguments(parser: ArgumentParser) -> None:
    # TODO: refactor and
    parser.add_argument(
        "-vcodec",
        "--vcodec",
        # choices=list(str_to_video_codec.keys()),
        default='h265',
        required=False,
        help="""Video encoder
\n"""
    )
    parser.add_argument(
        "-pix_fmt",
        "--pix_fmt",
        default="yuv422p10le",
        required=False,
        help="""FFMpeg pix_fmt. rgb/yuv only.
recommended: yuv420p, yuv422p10le, yuv422p12le
\n"""
    )

    parser.add_argument(
        "-preset",
        "--preset",
        choices=[
            'ultrafast',
            'superfast',
            'veryfast',
            'faster',
            'fast',
            'medium',
            'slow',
            'slower',
            'veryslow',
        ],
        default='',
        required=False,
        help="""FFmpeg video preset
\n"""
    )

    parser.add_argument(
        "-crf",
        "--crf",
        type=int,
        default=-1,
        required=False,
        help="""FFmpeg CRF
\n"""
    )

    parser.add_argument(
        "-tune",
        "--tune",
        choices=[
            'film',
            'animation',
            'grain',
            'stillimage',
            'fastdecode',
            'zerolatency',
        ],
        default='',
        help="""FFmpeg tune setting
\n"""
    )

    parser.add_argument(
        "-ffmpeg",
        "--ffmpeg",
        type=str,
        default="",
        help="""FFmpeg custom options.
\n"""
    )



def add_resize_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-resize",
        "--resize",
        type=float,
        default=1.,
        help="""Resize the video before applying any filter.
\n"""
    )

    parser.add_argument(
        "-resize_to",
        "--resize_to",
        type=str,
        default="",
        help="""Resize the video before applying any filter. Format: <width>x<height>.
example: -resize_to 640x480
\n"""
    )


def add_model_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "-m",
        "--model",
        type=str,
        default="",
        help="""Filepath to model (torch, engine)
\n"""
    )


def add_inference_arguments(parser: ArgumentParser) -> None:
    # Execution provider
    parser.add_argument(
        "--cuda",
        "-cuda",
        action="store_true",
        required=False,
        default=False,
        help="""Use the first cuda device as the execution provider.
Fallback to cpu if no CUDA device found.
\n"""
    )

#     parser.add_argument(
#         "--dml",
#         "-dml",
#         action="store_true",
#         required=False,
#         default=False,
#         help="""Use the DirectML as the execution provider.
# Ignored if the model is not an onnx model."
# \n"""
#     )

    parser.add_argument(
        "--cpu",
        "-cpu",
        action="store_true",
        required=False,
        default=False,
        help="""Use the CPU as the execution provider.
Ignored if the model is a TensorRT engine."
\n"""
    )

    # Precision
    parser.add_argument(
        "-fp32",
        "--fp32",
        action="store_true",
        required=False,
        help="""Inference with fp32 datatype
\n"""
    )

    parser.add_argument(
        "-fp16",
        "--fp16",
        action="store_true",
        required=False,
        help="""Inference with fp16 datatype
\n"""
    )

    parser.add_argument(
        "-bf16",
        "--bf16",
        action="store_true",
        required=False,
        help="""Inference with bf16 datatype
\n"""
    )

