from __future__ import annotations
from fractions import Fraction
from pathlib import Path
from hytils import (
    absolute_path,
    path_split,
    lightcyan,
    red,
    yellow,
)
import json
import os
from pprint import pformat, pprint
import subprocess
from warnings import warn

from .colorpspace import ColorRange

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


def probe_media_file(media_filepath: Path):
    ffprobe_command = [
        ffprobe_exe,
        "-v", "error",
        '-show_format',
        '-show_streams',
        '-of','json',
        str(media_filepath)
    ]
    process = subprocess.run(ffprobe_command, stdout=subprocess.PIPE)
    return json.loads(process.stdout.decode('utf-8'))



def open(filepath: Path) -> MediaStream | None:
    in_video_fp: Path = filepath.resolve()
    dlogger.debug(f"{lightcyan(f"Input video file:")} {in_video_fp}")

    if not in_video_fp.is_file(follow_symlinks=True):
        raise ValueError(red(f"Error: missing input file {in_video_fp}"))

    extension = in_video_fp.suffix
    if extension not in supported_video_exts:
        raise NotImplementedError(f"Not a supported video file (extension={extension})")

    try:
        media_info = probe_media_file(in_video_fp)
        duration_s = float(media_info['format']['duration'])

    except:
        dlogger.debug(pformat(media_info))
        raise ValueError(f"Failed to open {in_video_fp}")

    dlogger.debug(pformat(media_info))

    # Use the first video track
    v_stream: dict[str, str] = [
        stream
        for stream in media_info['streams']
        if stream['codec_type'] == 'video'
    ][0]
    audio_info: AudioInfo = AudioInfo(
        nstreams=len([
            stream
            for stream in media_info['streams']
            if stream['codec_type'] == 'audio'
        ])
    )
    subs_info: SubtitleInfo = SubtitleInfo(
        nstreams=len([
            stream
            for stream in media_info['streams']
            if stream['codec_type'] == 'subtitle'
        ])
    )

    # Video stream
    # Only first stream is used
    # Determine nb of channels and bpp
    is_supported: bool = False
    pix_fmt = v_stream.get('pix_fmt', None)
    try:
        v = PIXEL_FORMATS[pix_fmt]
        is_supported = v['supported']
        shape = (v_stream['height'], v_stream['width'], v['nc'])

    except:
        print(pix_fmt)
        raise
        pass

    if not is_supported:
        warn(yellow(f"{pix_fmt} is not supported"))

    field_order = FieldOrder._value2member_map_[v_stream.get('field_order', 'progressive')]

    # Frame rate
    frame_rate_r = v_stream.get('r_frame_rate', None)
    frame_rate_avg = v_stream.get('avg_frame_rate', None)
    if (
        frame_rate_avg is None
        or frame_rate_avg == "0/0"
    ):
        frame_rate_avg = frame_rate_r

    # Create a VideoStream instance and work with this
    video_info: VideoStream = VideoStream(
        filepath=in_video_fp,
        shape=shape,
        sar=Fraction(v_stream.get('sample_aspect_ratio', '1:1').replace(':', '/')),
        dar=Fraction(v_stream.get('display_aspect_ratio', '1:1').replace(':', '/')),

        field_order=field_order,

        frame_rate_r=Fraction(frame_rate_r), # pyright: ignore[reportCallIssue]
        frame_rate_avg=Fraction(frame_rate_avg), # pyright: ignore[reportCallIssue]

        codec=v_stream['codec_name'],
        pix_fmt=pix_fmt,
        # Colors
        color_space=v_stream.get('color_space', None),
        color_matrix=v_stream.get('color_matrix', None),
        color_transfer=v_stream.get('color_transfer', None),
        color_primaries=v_stream.get('color_primaries', None),
        # color_range=v_stream.get('color_range', None),

        duration=duration_s,
        metadata=v_stream.get('tags', None),
        frame_count=0,
    )

    color_range = v_stream.get('color_range', None)
    if color_range is not None:
        if color_range in ('pc', 'full'):
            video_info.color_range = ColorRange.FULL
        elif color_range in ('tv', 'limited'):
            video_info.color_range = ColorRange.LIMITED

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

    # Detect if dnxhd or dnxhr
    if video_info.codec == "dnxhd":
        profile = v_stream.get('profile', "").lower()
        if "dnxhr" in profile:
            video_info.codec = "dnxhr"
            for p in CODEC_PROFILE[VideoCodec.DNXHR].available:
                if p in profile:
                    video_info.profile = p.upper()

    # Tags for DNxHD / DNxHR are stored in format struct
    if video_info.codec == VideoCodec.DNXHR:
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

    # Is interlaced?
    if fo := v_stream.get('field_order', None):
        video_info.is_interlaced = bool(fo != FieldOrder.PROGRESSIVE.value)
    video_info.is_frame_rate_fixed = bool(video_info.frame_rate_r == video_info.frame_rate_avg)

    video_info.frame_count = int(
        (video_info.duration * video_info.frame_rate_r) + 0.5
    )

    tags = v_stream.get('tags', None)
    if tags is not None:
        tag_frame_count = tags.get('NUMBER_OF_FRAMES', '')
        if tag_frame_count is not None and tag_frame_count:
            tag_frame_count: int = int(tag_frame_count)
            if video_info.frame_count != tag_frame_count:
                video_info.frame_count = tag_frame_count
                video_info.frame_rate_r = Fraction(tag_frame_count, video_info.duration)
                video_info.frame_rate_avg = video_info.frame_rate_r
                print(yellow("modified frame_rate_avg using video_info.frame_count"))

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
        duration=0,
    )

    mstream: MediaStream=MediaStream(
        filepath=filepath,
        video=vstream,
        audio=AudioInfo(nstreams=0),
        subtitles=SubtitleInfo(nstreams=0),
    )
    vstream.parent = mstream

    return mstream
