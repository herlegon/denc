from hytils import absolute_path
import multiprocessing
import os
from pprint import pprint
import shutil
import signal
import time

import numpy as np
import denc



def main():
    cpu_count: int = int(3 * multiprocessing.cpu_count() / 4)
    cpu_count: int = multiprocessing.cpu_count()

    # Load images, limit to 20 imes
    in_img_dir: str = absolute_path(f"~/mco/imgs/ep10_226_lr_j")
    in_img_fp: list[str] = sorted(
        [os.path.join(in_img_dir, f) for f in os.listdir(in_img_dir) if f.endswith(".png")]
    )
    in_img_fp = in_img_fp[:20]
    in_images = denc.load_images(
        filepaths=in_img_fp, cpu_count=cpu_count, dtype=np.float32
    )

    # Save to a different folder
    out_img_dir: str = f"{in_img_dir}_out"
    os.makedirs(out_img_dir, exist_ok=True)
    out_img_fp: list[str] = sorted(
        [os.path.join(out_img_dir, f) for f in os.listdir(in_img_dir) if f.endswith(".png")]
    )

    # Multiprocessing
    start_time = time.time()
    denc.write_images(
        filepaths=out_img_fp, images=in_images, cpu_count=cpu_count
    )
    elapsed = time.time() - start_time
    print(f"write {len(in_images)} images in {1000 * (elapsed):.01f}ms ({len(in_images)/elapsed:.01f}fps) (cpu_count={cpu_count})")


    # Single process
    shutil.rmtree(out_img_dir)
    start_time = time.time()
    denc.write_images(
        filepaths=out_img_fp, images=in_images, cpu_count=1
    )
    elapsed = time.time() - start_time
    print(f"write {len(in_images)} images in {1000 * (elapsed):.01f}ms ({len(in_images)/elapsed:.01f}fps) (cpu_count=1)")

    # Clean
    shutil.rmtree(out_img_dir)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()



