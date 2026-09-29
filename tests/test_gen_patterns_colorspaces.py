from argparse import ArgumentParser
from dataclasses import dataclass
from enum import Enum, IntEnum
import os
from pprint import pprint
import signal
import subprocess
import sys
import time
from typing import Any

from helpers.p_print import *
from path_utils import absolute_path
py_temporalfix_dir: str = os.path.abspath(os.path.join(os.getcwd(), os.pardir, "py_temporalfix"))
if not os.path.exists(py_temporalfix_dir):
    if sys.platform == "linux":
        py_temporalfix_dir: str = os.path.abspath(
            os.path.join(os.path.expanduser("~"), "github", "py_temporalfix")
        )
    else:
        py_temporalfix_dir: str = os.path.abspath(
            os.path.join("A:", "py_temporalfix")
        )
sys.path.append(py_temporalfix_dir)
from utils.tools import ffmpeg_exe
from media.vinfo import VideoInfo, extract_media_info


# yuvtestsrc, smptehdbars, colorchart
# unknown, rec.601, rec.709, bt2020
# limited, full
# yuv420p, yuv422p10
# h264, h265, ffv1, DNxHR, vp9

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
vcodec_profile: dict[VideoCodec, str] = {
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
    RGB24 = 'rgb24'
    RGB48 = 'rgb48'


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


not_supported_colorspace: dict[VideoCodec, list[Colorspace]] = {
    VideoCodec.H264: [],
    VideoCodec.H265: [],
    VideoCodec.FFV1: [],
    VideoCodec.DNXHR: [Colorspace.REC601_PAL, Colorspace.REC601_NTSC],
    VideoCodec.VP9: [],
}


class Size(Enum):
    SIZE_3840_2160 = "3840x2160"
    SIZE_1920_1080 = "1920x1080"
    SIZE_1280_720 = "1280x720"
    SIZE_720_576 = "720x576"


supported_pixfmt: dict[VideoCodec, tuple[PixFmt]] = {
    VideoCodec.H264: (PixFmt.YUV420P,),
    VideoCodec.H265: (PixFmt.YUV420P, PixFmt.YUV422P10),
    VideoCodec.FFV1: (PixFmt.YUV420P, PixFmt.YUV422P10, PixFmt.RGB24, PixFmt.RGB48),
    VideoCodec.DNXHR: (PixFmt.YUV420P, PixFmt.YUV422P10),
    VideoCodec.VP9: (PixFmt.YUV420P, PixFmt.YUV422P10),
}


@dataclass
class PatternParams:
    vcodec: VideoCodec
    pattern: PatternName
    color_range: ColorRange
    pix_fmt: PixFmt
    colorspace: Colorspace
    size: Size
    out_dir: str = "."

    def __post_init__(self):
        filepath_pattern = "{codec}_{size}_{pix_fmt}_{colorspace}_{range}_{pattern}{ext}"
        filename: str = filepath_pattern.format(
            codec=self.vcodec.value,
            size=self.size.value,
            pix_fmt=self.pix_fmt.value,
            colorspace=self.colorspace.value,
            range=self.color_range.value,
            pattern=pretty_pattern_name[self.pattern],
            ext=vcodec_to_extension[self.vcodec],
        )
        self._filepath: str = os.path.join(absolute_path(self.out_dir), filename)

    @property
    def filepath(self) -> str:
        return self._filepath



def main():
    parser = ArgumentParser()
    parser.add_argument(
        "--codec",
        "-c",
        choices=['all'] + [e.value for e in VideoCodec],
        default='all',
        required=False,
    )
    parser.add_argument(
        "--pattern",
        "-p",
        choices=['all'] + [e.value for e in PatternName],
        default='all',
        required=False,
    )
    parser.add_argument(
        "--range",
        "-r",
        choices=['all'] + [e.value for e in ColorRange],
        default='all',
        required=False,
    )
    parser.add_argument(
        "--pix_fmt",
        "-pix_fmt",
        choices=['all'] + [e.value for e in PixFmt],
        default='all',
        required=False,
    )
    parser.add_argument(
        "--colorpsace",
        "-colorspace",
        choices=['all'] + [e.value for e in Colorspace],
        default='all',
        required=False,
    )
    parser.add_argument(
        "--size",
        "-size",
        choices=['all'] + [e.value for e in Size],
        default='all',
        required=False,
    )
    parser.add_argument(
        "--t",
        "-t",
        type=int,
        default=3,
        required=False,
    )
    parser.add_argument(
        "--frame_rate",
        "-fps",
        type=str,
        default="25",
        required=False,
    )


    arguments = parser.parse_args()

    def _get_enum_key(v: str, enumClass: Enum) -> Any:
        return enumClass.__dict__[enumClass(v).name]

    def generate_list(arg: str, enumClass: Enum) -> list[Any]:
        return list(
            [e for e in enumClass]
            if arg == 'all'
            else [_get_enum_key(arg, enumClass)]
        )


    codecs: list[VideoCodec] = generate_list(arguments.codec, VideoCodec)
    patterns: list[PatternName] = generate_list(arguments.pattern, PatternName)
    ranges: list[ColorRange] = generate_list(arguments.range, ColorRange)
    pix_fmts: list[PixFmt] = generate_list(arguments.pix_fmt, PixFmt)
    colorspaces: list[Colorspace] = generate_list(arguments.colorpsace, Colorspace)
    sizes: list[Size] = generate_list(arguments.size, Size)


    # simplify:
    try:
        codecs.remove(VideoCodec.VP9)
    except:
        pass
    try:
        colorspaces.remove(Colorspace.BT2020C)
    except:
        pass
    # for c in (Colorspace.BT2020NC, Colorspace.BT2020C):
    #     try:
    #         colorspaces.remove(c)
    #     except:
    #         pass
    # try:
    #     sizes.remove(Size.SIZE_3840_2160)
    # except:
    #     pass


    print(codecs)
    print(patterns)
    print(ranges)
    print(pix_fmts)
    print(colorspaces)
    print(sizes)
    pprint(supported_pixfmt)

    out_dir: str = absolute_path("patterns_in")
    os.makedirs(out_dir, exist_ok=True)


    # Generate a list of parameters for each scenario
    scenarii: list[PatternParams] = []
    for codec in codecs:
        for pix_fmt in pix_fmts:
            if pix_fmt not in supported_pixfmt[codec]:
                print(yellow("Skip:"), f"{codec.value}, {pix_fmt.value}")
                continue

            for pattern in patterns:
                for colorspace in colorspaces:
                    if colorspace in not_supported_colorspace[codec]:
                        print(yellow("Skip:"), f"{codec.value}, {colorspace.value}")
                        continue

                    if (
                        colorspace in (Colorspace.BT2020C, Colorspace.BT2020C)
                        and pix_fmt != PixFmt.YUV422P10
                    ):
                        print(yellow("Skip:"), f"{codec.value}, {colorspace.value}, {pix_fmt.value}")
                        continue

                    for size in sizes:
                        for _range in ranges:
                            scenarii.append(
                                PatternParams(
                                    vcodec=codec,
                                    size=size,
                                    pix_fmt=pix_fmt,
                                    colorspace=colorspace,
                                    color_range=_range,
                                    pattern=pattern,
                                    out_dir=out_dir
                                )
                            )
                            if pattern == PatternName.COLORCHART:
                                break

    pprint([p.filepath for p in scenarii])
    print(len(scenarii))

    def _clean_str(line: str):
        cleaned: str = line
        for c in ('\\', '\"', ' ', '\r', '\n'):
            cleaned = cleaned.replace(c, '')
        return cleaned.strip()

    for scenario in scenarii:
        # Pattern
        input: str = f"""
            {scenario.pattern.value}=
            rate={arguments.frame_rate}
            :duration={arguments.t}
        """
        if pattern != PatternName.COLORCHART:
            input += f":size={scenario.size.value}"
        input: str = _clean_str(input)

        # Codec, profile
        profile_args: list[str] = []
        if vcodec_profile[scenario.vcodec]:
            profile_args = ["-profile", vcodec_profile[scenario.vcodec]]

        # Colorspace
        colorspace_args: list[str] = []
        space, prim, trc = colorspace_to_params[scenario.colorspace]
        if scenario.vcodec == VideoCodec.H264:
            colorspace_args = [
                "-x264-params",
                f"colorspace={space}:colorprim={prim}:transfer={trc}"
            ]
            colorspace_args.extend([
                "-colorspace", space,
                "-color_primaries", prim,
                "-color_trc", trc
            ])

        elif scenario.vcodec == VideoCodec.H265:
            colorspace_args = [
                "-x265-params",
                f"colorprim={prim}:transfer={trc}:colormatrix={space}"
            ]

        # if scenario.vcodec == VideoCodec.FFV1:

        elif scenario.vcodec == VideoCodec.DNXHR:
            colorspace_args = [
                "-vf",
                _clean_str(f"""
                    setparams=colorspace={space}
                        :color_primaries={prim}
                        :color_trc={trc}
                """),
            ]

        # if scenario.vcodec == VideoCodec.VP9:

        # Finally, FFmpeg command
        ffmpeg_command: list[str] = [
            ffmpeg_exe,
            "-hide_banner",
            "-loglevel", "error",
            "-stats",
            "-f", "lavfi",
            "-i", input,
            "-c:v", vcodec_to_ffmpeg_vcodec[scenario.vcodec],
            *profile_args,
            "-pix_fmt", scenario.pix_fmt.value,
            *colorspace_args,
            "-color_range", scenario.color_range.value,
            "-y",
            scenario.filepath
        ]
        print(lightcyan("Encoder command:"))
        print(lightgreen(' '.join(ffmpeg_command)))

        result = subprocess.run(
            ffmpeg_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        for std in (result.stdout, result.stderr):
            std_str: str = ''
            try:
                std_str = std.decode('utf-8')
            except:
                pass
            if std_str:
                for l in std_str:
                    if not l.startswith("x265 [info]"):
                        print(l.strip())

        out_vi: VideoInfo = extract_media_info(scenario.filepath)['video']
        report: str = f"  {lightcyan("space:")} {out_vi['color_space']}"
        report += f", {lightcyan("prim:")} {out_vi['color_primaries']}"
        report += f", {lightcyan("transfer:")} {out_vi['color_transfer']}"
        # report += f", {lightcyan("matrix:")} {out_vi['color_matrix']}"
        report += f", {lightcyan("range:")} {out_vi['color_range']}"
        print(report)

        color_range_values: list[str] = (
            ["pc", "full", "jpeg"]
            if scenario.color_range == ColorRange.FULL
            else ["tv", "limited", "restricted", "mpeg"]
        )
        if out_vi['color_space'] != space:
            print(red("Error:"), f" {out_vi['color_space']} should be {space}")
        if out_vi['color_primaries'] != prim:
            print(red("Error:"), f" {out_vi['color_primaries']} should be {prim}")

        if trc == 'gamma28':
            trc = 'bt470bg'
        if out_vi['color_transfer'] != trc:
            print(red("Error:"), f" {out_vi['color_transfer']} should be {trc}")
        if out_vi['color_range'] not in color_range_values:
            print(red("Error:"), f" {out_vi['color_range']} should be in {color_range_values}")
        print()

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()



