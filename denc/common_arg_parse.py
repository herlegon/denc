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
    parser.add_argument(
        "-s",
        "--strength",
        type=BoundedInteger(1, 800),
        metavar="[1..800]",
        default=400,
        required=False,
        help="""Suppression strength of temporal inconsistencies.
Higher means more aggressive.
\n"""
    )

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



def add_debug_arguments(parser: ArgumentParser) -> None:
    parser.add_argument(
        "--debug",
        action="store_true",
        required=False,
        help="Enable verbose output for debugging."
    )
