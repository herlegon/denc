import logging
from pprint import pformat
from typing import Literal
from hytils import lightcyan, lightgreen, red
from pathlib import Path
import signal
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.utils import ParsedFilename, parse_filename
import denc
from denc import (
    MediaStream,
    dlogger,
)




def main():
    dlogger.setLevel(logging.DEBUG)
    results: dict[str, Literal['passed', 'failed']] = {}

    # a list of images
    in_video_dir: Path = Path(__file__).resolve().parents[1] / "out" / "img_to_video"
    in_video_filepaths = sorted(Path(in_video_dir).glob("*"))

    for fp in in_video_filepaths:
        f_name = fp.name
        parsed_filename: ParsedFilename = parse_filename(f_name)
        print(lightcyan(f_name))
        print(parsed_filename)
        print()

        if False:
            try:
                media: MediaStream = denc.open(fp)
                dlogger.info(f"\t{media.video.pipe_format}")
                dlogger.info(pformat(media.video))

            except Exception as e:
                dlogger.error(red(f"\t{e}"))
                results[f_name] = 'failed'
                continue

        else:
            media: MediaStream = denc.open(fp)
            dlogger.info(f"\t{media.video.pipe_format}")
            dlogger.info(pformat(media.video))


        results[f_name] = 'passed'

    for f_name, r in results.items():
        color = lightgreen if r == 'passed' else red
        dlogger.info(f"{f_name:<60} {color(r)}")


    dlogger.info("Ended.")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()

