from pathlib import Path
import multiprocessing
import os
from pprint import pprint
import signal
import time

import numpy as np
import denc



def main():
    cpu_count: int = int(3 * multiprocessing.cpu_count() / 4)

    # a list of images, limit to 20 images
    in_img_dir: Path = Path(f"~/z-personnel/mco/imgs/ep10_226_lr_j")
    in_img_fp: list[str] = sorted(
        [os.path.join(in_img_dir, f) for f in os.listdir(in_img_dir) if f.endswith(".png")]
    )
    in_img_fp = in_img_fp[:20]
    # pprint(in_img_fp)


    start_time = time.time()
    in_images = denc.load_images(
        filepaths=in_img_fp, cpu_count=cpu_count, dtype=np.float32
    )
    elapsed = time.time() - start_time
    print(f"[np.float32] loaded {len(in_images)} images in {1000 * (elapsed):.01f}ms ({len(in_images)/elapsed:.01f}fps) (cpu_count={cpu_count})")


    start_time = time.time()
    in_images = denc.load_images(
        filepaths=in_img_fp, cpu_count=1, dtype=np.uint8
    )
    elapsed = time.time() - start_time
    print(f"[np.float32] loaded {len(in_images)} images in {1000 * (elapsed):.01f}ms ({len(in_images)/elapsed:.01f}fps) (cpu_count=1)")


    start_time = time.time()
    in_images = denc.load_images(
        filepaths=in_img_fp, cpu_count=cpu_count, dtype=np.uint8
    )
    elapsed = time.time() - start_time
    print(f"[np.float8] loaded {len(in_images)} images in {1000 * (elapsed):.01f}ms ({len(in_images)/elapsed:.01f}fps) (cpu_count={cpu_count})")


    start_time = time.time()
    in_images = denc.load_images(
        filepaths=in_img_fp[:0], cpu_count=cpu_count, dtype=np.float32
    )
    elapsed = time.time() - start_time
    print(f"[np.float32] loaded 1 images in {1000 * (elapsed):.01f}ms ({1/elapsed:.01f}fps)")



if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()



