from __future__ import annotations
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any
from hytils import (
    lightcyan,
    red,
    yellow,
)
import json
import os
from pprint import pformat, pprint
import subprocess
from warnings import warn

from .colorpspace import ColorInfo, ColorRange

from .media_stream import (
    AudioInfo,
    MediaStream,
    SubtitleInfo,
    VideoStream,
)
from .pxl_fmt import PIXEL_FORMATS, PixFmt
from .utils.tools import ffprobe_exe
from .utils.time_conversions import FrameRate
from .vcodec import VideoCodec, supported_video_exts, CODEC_PROFILE
from .vstream import FieldOrder, OutVideoStream
from .utils.dlogger import dlogger



def _parse_fraction(value: str | None, default: str) -> Fraction:
    # ffprobe can return "N/A", "0/0" or "0:0" when the value is unknown
    if not value or value in ("0/0", "0:0", "N/A"):
        value = default

    try:
        return Fraction(value.replace(":", "/"))
    except (ValueError, ZeroDivisionError):
        return Fraction(default.replace(":", "/"))



def _parse_color_range(value: str | None) -> ColorRange | None:
    if value in ("pc", "full"):
        return ColorRange.FULL

    if value in ("tv", "limited"):
        return ColorRange.LIMITED

    return None



def _frame_count_from_duration(
    duration: Decimal,
    frame_rate: Fraction,
) -> int:
    """
    Estimate the number of frames from duration and frame rate.
    duration is kept as Decimal because it comes from ffprobe.
    frame_rate is kept as Fraction for exact rational arithmetic.
    """
    if duration < 0:
        raise ValueError(f"Invalid negative duration: {duration}")

    if frame_rate <= 0:
        raise ValueError(f"Invalid frame rate: {frame_rate}")

    frame_count = (
        duration
        * Decimal(frame_rate.numerator)
        / Decimal(frame_rate.denominator)
    )
    return int(frame_count.to_integral_value(rounding=ROUND_HALF_UP))



def probe_media_file(media_filepath: Path) -> dict[str, Any]:
    ffprobe_command = [
        ffprobe_exe,
        "-v", "error",
        '-show_format',
        '-show_streams',
        '-of','json',
        str(media_filepath)
    ]
    try:
        process = subprocess.run(
            ffprobe_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as e:
        raise ValueError(
            f"ffprobe failed for {media_filepath}: "
            f"{e.stderr.strip()}"
        ) from e

    try:
        return json.loads(process.stdout)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid ffprobe JSON for {media_filepath}") from e



def open(filepath: Path) -> MediaStream | None:
    in_video_fp: Path = filepath.resolve()
    dlogger.debug(f"{lightcyan(f"Input video file:")} {in_video_fp}")

    if not in_video_fp.is_file(follow_symlinks=True):
        raise ValueError(red(f"Error: missing input file {in_video_fp}"))

    extension = in_video_fp.suffix.lower()
    if extension not in supported_video_exts:
        raise NotImplementedError(f"Not a supported video file (extension={extension})")

    try:
        media_info = probe_media_file(in_video_fp)
    except Exception as e:
        raise ValueError(f"Failed to probe {in_video_fp}") from e

    dlogger.debug(pformat(media_info))


    # Use the first video track
    v_streams: dict[str, str] = [
        stream for stream in media_info['streams'] if stream['codec_type'] == 'video'
    ]
    if not v_streams:
        raise ValueError(f"No video stream found in {in_video_fp}")
    v_stream: dict = v_streams[0]

    audio_info: AudioInfo = AudioInfo(
        nstreams=len([
            stream for stream in media_info['streams'] if stream['codec_type'] == 'audio'
        ])
    )
    subs_info: SubtitleInfo = SubtitleInfo(
        nstreams=len([
            stream for stream in media_info['streams'] if stream['codec_type'] == 'subtitle'
        ])
    )

    # Pixel format
    pix_fmt = v_stream.get('pix_fmt', None)
    try:
        pixel_format = PIXEL_FORMATS[pix_fmt]
    except KeyError as e:
        raise ValueError(
            f"Unknown pixel format {pix_fmt!r} "
            f"for {in_video_fp}"
        ) from e

    is_supported: bool = pixel_format["supported"]
    if not is_supported:
        warn(yellow(f"{pix_fmt} is not supported"))

    # Frame shape
    shape = (v_stream["height"], v_stream["width"], pixel_format["nc"])

    # Field order
    field_order_value = v_stream.get("field_order", FieldOrder.PROGRESSIVE.value)
    try:
        field_order = FieldOrder(field_order_value)
    except ValueError:
        dlogger.warning(f"Unknown field_order={field_order_value!r}; using progressive")
        field_order = FieldOrder.PROGRESSIVE
    is_interlaced = bool(field_order != FieldOrder.PROGRESSIVE)

    # Color information
    # ffprobe:
    #   color_space     -> YCbCr matrix coefficients
    #   color_primaries -> chromatic primaries
    #   color_transfer  -> transfer characteristic
    color_info = ColorInfo(
        matrix=v_stream.get("color_space"),
        primaries=v_stream.get("color_primaries"),
        transfer=v_stream.get("color_transfer"),
        range=_parse_color_range(v_stream.get("color_range")),
    )

    # Duration
    format_info = media_info.get("format") or {}
    duration_value = format_info.get("duration")
    if duration_value is None:
        raise ValueError(f"Missing duration in ffprobe output for {in_video_fp}")

    try:
        duration = Decimal(str(duration_value))
    except (InvalidOperation, TypeError, ValueError) as e:
        raise ValueError(f"Invalid duration {duration_value!r} for {in_video_fp}") from e

    if duration < 0:
        raise ValueError(f"Invalid negative duration {duration} for {in_video_fp}")

    # Frame rate
    frame_rate_r_value = v_stream.get("r_frame_rate")
    frame_rate_avg_value = v_stream.get("avg_frame_rate")
    if not frame_rate_r_value or frame_rate_r_value == "0/0":
        raise ValueError(f"Missing/invalid r_frame_rate for {in_video_fp}")
    if not frame_rate_avg_value or frame_rate_avg_value == "0/0":
        frame_rate_avg_value = frame_rate_r_value

    try:
        frame_rate_r = Fraction(frame_rate_r_value)
        frame_rate_avg = Fraction(frame_rate_avg_value)
    except (ValueError, ZeroDivisionError) as e:
        raise ValueError(
            f"Invalid frame rate: "
            f"r_frame_rate={frame_rate_r_value!r}, "
            f"avg_frame_rate={frame_rate_avg_value!r} "
            f"for {in_video_fp}"
        ) from e

    # Frame count
    frame_count = _frame_count_from_duration(duration, frame_rate_r)


    # Optional NUMBER_OF_FRAMES tag
    tags = v_stream.get("tags") or {}
    tag_frame_count_raw = tags.get("NUMBER_OF_FRAMES")
    if tag_frame_count_raw:
        try:
            tag_frame_count = int(tag_frame_count_raw)
        except (TypeError, ValueError):
            dlogger.warning(
                f"Invalid NUMBER_OF_FRAMES={tag_frame_count_raw!r} "
                f"for {in_video_fp}"
            )
        else:
            if tag_frame_count < 0:
                dlogger.warning(
                    f"Invalid negative NUMBER_OF_FRAMES="
                    f"{tag_frame_count_raw!r} for {in_video_fp}"
                )
            else:
                if tag_frame_count != frame_count:
                    dlogger.debug(
                        f"NUMBER_OF_FRAMES={tag_frame_count} differs "
                        f"from duration-derived frame count="
                        f"{frame_count} "
                        f"for {in_video_fp}"
                    )
                # The explicit frame-count metadata wins.
                frame_count = tag_frame_count

    # Video Codec
    vcodec_name = v_stream.get("codec_name", "")
    vcodec_name = {
        "hevc": "h265",
    }.get(vcodec_name, vcodec_name)
    if not vcodec_name:
        raise NotImplementedError(f"Video Codec \'{vcodec_name}\' is not supported")
    v_codec = VideoCodec(vcodec_name)
    v_profile = ""
    if v_codec in (VideoCodec.DNXHR, VideoCodec.DNXHD):
        # if DNxHD or DNxHR, profile has to be used too
        v_profile = v_stream.get("profile", "").lower()
        if "dnxhr" in v_profile:
            v_codec = VideoCodec.DNXHR
            for p in CODEC_PROFILE[VideoCodec.DNXHR].available:
                if p in v_profile:
                    v_profile = p.upper()
                    break

    # Video stream
    video_info = VideoStream(
        filepath=in_video_fp,
        shape=shape,

        sar=_parse_fraction(v_stream.get("sample_aspect_ratio"), "1:1"),
        dar=_parse_fraction(v_stream.get("display_aspect_ratio"), "1:1"),

        field_order=field_order,
        interlaced=is_interlaced,

        frame_rate_r=frame_rate_r,
        frame_rate_avg=frame_rate_avg,
        is_frame_rate_fixed=bool(frame_rate_r == frame_rate_avg),
        frame_count=frame_count,
        duration=duration,

        codec=v_codec,
        profile=v_profile,
        pix_fmt=pix_fmt,
        color=color_info,

        metadata=v_stream.get("tags") or {},
    )

    # Tags to discard
    tags_to_discard: tuple[str, ...]
    if isinstance(video_info.metadata, dict):
        tags_to_discard = (
            'duration',
            'encoder',
            'creation_time',
            'handler_name',
            'vendor_id',
            'file_package_umid'
        )
        tag_name: str
        for tag_name in list(video_info.metadata.keys()).copy():
            if tag_name.lower() in tags_to_discard:
                try:
                    del video_info.metadata[tag_name]
                except:
                    pass

    # Tags for DNxHD / DNxHR are stored in format struct
    if v_codec == VideoCodec.DNXHR:
        tags_to_discard = (
            'application_platform',
            'company_name',
            'generation_uid',
            'material_package_umid',
            'operational_pattern_ul',
            'product_name',
            'product_uid',
            'product_version',
            'product_version_num',
            'timecode',
            'toolkit_version_num',
            'uid',
        )

        tags: dict[str, str]
        if tags := media_info['format']['tags']:
            tag_name: str
            for tag_name in list(tags.keys()).copy():
                if tag_name.lower() in tags_to_discard:
                    try:
                        del video_info.metadata[tag_name]
                    except:
                        pass
                    continue
                video_info.metadata[tag_name] = tags[tag_name]

    return MediaStream(
        filepath=filepath,
        video=video_info,
        audio=audio_info,
        subtitles=subs_info
    )



def new(filepath: str = "", preset = None) -> MediaStream:
    vstream = OutVideoStream(
        filepath=filepath,
        codec=VideoCodec.H265,
        pix_fmt=PixFmt.YUV422P10,
        shape=(0, 0, 0),
        frame_rate_r=FrameRate(25, 1),
        frame_rate_avg=FrameRate(25, 1),
        frame_count=0,
        duration=Decimal(),
    )

    mstream: MediaStream=MediaStream(
        filepath=filepath,
        video=vstream,
        audio=AudioInfo(nstreams=0),
        subtitles=SubtitleInfo(nstreams=0),
    )
    vstream.parent = mstream

    return mstream
