import os
from pathlib import Path
import sys
from stat import S_IEXEC


ORGANIZATION = "herlegon"

if sys.platform == "win32":
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / "AppData" / "Local"))
    ffmpeg_dir = base / ORGANIZATION / "ffmpeg" / "bin"
    ffmpeg_exe: str = str(ffmpeg_dir / "ffmpeg.exe")
    ffprobe_exe: str = str(ffmpeg_dir / "ffprobe.exe")

elif sys.platform == "linux":
    base = Path(os.environ.get('XDG_DATA_HOME', Path.home() / ".local" / "share"))
    ffmpeg_dir = base / ORGANIZATION / "ffmpeg" / "bin"
    ffmpeg_exe: str = str(ffmpeg_dir / "ffmpeg")
    ffprobe_exe: str = str(ffmpeg_dir / "ffprobe")

    # Make them executable if not already done
    try:
        for f in [ffmpeg_exe, ffprobe_exe]:
            st_mode = os.stat(f).st_mode
            if oct(st_mode & 0o100) == "0o0":
                os.chmod(f, st_mode |S_IEXEC)
    except:
        pass

else:
    raise NotImplementedError(f"{sys.platform} is not a supported platform")
