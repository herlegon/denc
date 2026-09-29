from argparse import ArgumentParser
from enum import Enum, IntEnum
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

from hytils import lightcyan


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
    VP9 = "VP9"
    PRORES = "ProRes"


vcodec_to_ffmpeg_vcodec: dict[VideoCodec, str] = {
    VideoCodec.H264: "libx264",
    VideoCodec.H265: "libx265",
    VideoCodec.VP9: "libvpx-vp9",
    VideoCodec.FFV1: "ffv1",
    VideoCodec.DNXHR: "dnxhd",
    VideoCodec.PRORES: "prores_ks",
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
    VideoCodec.FFV1: ".mkv",
    VideoCodec.VP9: ".mkv",
    VideoCodec.DNXHR: ".mxf",
    VideoCodec.PRORES: ".mov",
}


class ColorRange(Enum):
    LIMITED = "limited"
    FULL = "full"


class PixFmt(Enum):
    YUV420P = "yuv420p"
    YUV422P10 = "yuv422p10le"
    RGB24 = "rgb24"
    RGB48 = "rgb48"


class Colorspace(Enum):
    UNKNOWN = "unknown"
    REC601_PAL = "rec601_pal"
    REC601_NTSC = "rec601_ntsc"
    REC709 = "bt709"
    BT2020NC = "bt2020nc"
    BT2020C = "bt2020c"


colorspace_to_params = {
    # colorspace, primaries, transfer
    Colorspace.UNKNOWN: ("unknown", "unknown", "unknown"),
    Colorspace.REC601_PAL: ("bt470bg", "bt470bg", "gamma28"),
    Colorspace.REC601_NTSC: ("smpte170m", "smpte170m", "smpte170m"),
    Colorspace.REC709: ("bt709", "bt709", "bt709"),
    Colorspace.BT2020NC: ("bt2020nc", "bt2020", "bt2020-10"),
    Colorspace.BT2020C: ("bt2020c", "bt2020", "bt2020-10"),
}


pixfmts: dict[VideoCodec, tuple[PixFmt]] = {
    VideoCodec.H264: (PixFmt.YUV420P,),
    VideoCodec.H265: (PixFmt.YUV420P, PixFmt.YUV422P10),
    VideoCodec.FFV1: (PixFmt.RGB24, PixFmt.RGB48),
    VideoCodec.DNXHR: (PixFmt.YUV422P10,),
    VideoCodec.VP9: (PixFmt.YUV420P, PixFmt.YUV422P10),
    VideoCodec.PRORES: (PixFmt.YUV422P10,),
}



def _clean_str(line: str):
    cleaned: str = line
    for c in ('\\', '\"', ' ', '\r', '\n'):
        cleaned = cleaned.replace(c, '')
    return cleaned.strip()



def build_ffmpeg_command(
    out_dir: Path,
    size: str = "",
    vcodec: VideoCodec = VideoCodec.H265,
    profile: str = "",
    pix_fmt: PixFmt = PixFmt.YUV422P10,
    frame_rate: int | float = 25,
    duration: int = 60,
    pattern_name: PatternName = PatternName.SMPTEHDBARS,
    colorspace: Colorspace | None = None,
    color_range: ColorRange = None,
    add_grain: bool = True,
    overwrite: bool = True,
    ffmpeg_exe: str = "ffmpeg",
) -> tuple[Path, list[str]]:

    # Pattern
    pattern: str = f"{pattern_name.value}=rate={frame_rate}:duration={duration}"
    if pattern_name != PatternName.COLORCHART:
        if wh := re.search(re.compile(r"(\d+)x(\d+)"), size):
            size = "x".join(map(str, map(int, wh.groups())))
        else:
            raise ValueError(f"Error: size must be in WxH format (e.g. 1280x768). Got {size}")

        pattern += f":size={size}"


    # Simple filters
    simple_filters: list[str] = []
    if add_grain:
        simple_filters = ["-vf", "noise=alls=10:allf=t"]


    # Codec profile
    profile_args: list[str] = []
    profile = vcodec_default_profile.get(vcodec, "")
    if profile:
        profile_args = ["-profile", profile]


    # Colorspace
    colorspace_args: list[str] = []
    if colorspace is not None:
        space, prim, trc = colorspace_to_params[colorspace]
        if vcodec == VideoCodec.H264:
            colorspace_args = [
                "-x264-params",
                f"colorspace={space}:colorprim={prim}:transfer={trc}"
            ]
            colorspace_args.extend([
                "-colorspace", space,
                "-color_primaries", prim,
                "-color_trc", trc
            ])

        elif vcodec == VideoCodec.H265:
            colorspace_args = [
                "-x265-params",
                f"colorprim={prim}:transfer={trc}:colormatrix={space}"
            ]

        elif vcodec == VideoCodec.DNXHR:
            colorspace_args = [
                "-vf",
                _clean_str(f"""
                    setparams=colorspace={space}
                        :color_primaries={prim}
                        :color_trc={trc}
                """),
            ]

    # Color Range
    color_range_args: list[str] = []
    if color_range is not None:
        color_range_args = ["-color_range", color_range.value]


    # Filename
    filename: str = "_".join([
        pretty_pattern_name[pattern_name], vcodec.value, size, pix_fmt.value
    ])
    if colorspace_args:
        filename += f"_{colorspace.value}"
    if color_range_args:
        filename += f"_{color_range.value}"
    filename += vcodec_to_extension.get(vcodec, ".mkv")
    filepath: Path = out_dir / filename

    # Finally, FFmpeg command
    ffmpeg_command: list[str] = [
        ffmpeg_exe,
        "-hide_banner",
        "-loglevel", "error",
        "-stats",
        "-f", "lavfi",
        "-i", pattern,
        *simple_filters,
        "-c:v", vcodec_to_ffmpeg_vcodec[vcodec],
        *profile_args,
        "-pix_fmt", pix_fmt.value,
        *colorspace_args,
        *color_range_args,
        str(filepath),
        "-y" if overwrite else "",
    ]
    ffmpeg_command = list([v for v in ffmpeg_command if v])

    return filepath, ffmpeg_command




def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--duration",
        "-t",
        type=float,
        default=5,
        required=False,
        help="Duration in seconds, default: 60",
    )
    parser.add_argument(
        "--out_dir",
        "-o",
        type=str,
        default="",
        required=False,
        help="Output directory, default: `../../video-patterns`",
    )
    arguments = parser.parse_args()

    ffmpeg_exe = "ffmpeg"
    if arguments.out_dir:
        out_dir: Path = Path(arguments.out_dir).resolve()
    else:
        out_dir: Path = Path(__file__).resolve().parents[2] / "video-patterns"

    duration = arguments.duration

    resolutions: tuple[str] = (
        "640x480",
        "720x540",
        "720x576",
        "1280x720",
        "1920x1080",
        # "3840x2160",
    )
    codecs: list = list([e for e in VideoCodec])
    for c in (VideoCodec.VP9, VideoCodec.FFV1):
        try:
            codecs.remove(c)
        except:
            pass


    # Create a dict: felipath, command
    scenarii: dict[Path, list[str]] = {}
    for resolution in resolutions:
        for vcodec in codecs:

            default_profile = vcodec_default_profile.get(vcodec, "")
            for pix_fmt in pixfmts[vcodec]:
                fp, command = (
                    build_ffmpeg_command(
                        out_dir=out_dir,
                        size=resolution,
                        duration=duration,
                        pattern_name=PatternName.SMPTEHDBARS,
                        colorspace=Colorspace.REC709,
                        color_range=ColorRange.LIMITED,
                        vcodec=vcodec,
                        pix_fmt=pix_fmt,
                        profile=default_profile,
                        add_grain=True,
                        ffmpeg_exe=ffmpeg_exe
                    )
                )
                scenarii[fp] = command

    os.makedirs(out_dir, exist_ok=True)
    fp: Path
    for fp, ffmpeg_command in scenarii.items():
        print(lightcyan(fp.name))
        print(' '.join(ffmpeg_command))

        ffmpeg_subprocess: subprocess.Popen | None = None
        try:
            ffmpeg_subprocess = subprocess.Popen(
                ffmpeg_command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )
        except Exception as e:
            print(f"[E] Unexpected error: {type(e)}", flush=True)

        os.set_blocking(ffmpeg_subprocess.stdout.fileno(), False)
        try:
            while True:
                if ffmpeg_subprocess.poll() is not None:
                    break

                line: str = ffmpeg_subprocess.stdout.readline().decode('utf-8')
                if (
                    line
                    and not line.startswith("x265 [info]")
                ):
                    print(line, file=sys.stderr, flush=True, end='')
            print()
        except:
            pass

    print(len(scenarii))

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()



