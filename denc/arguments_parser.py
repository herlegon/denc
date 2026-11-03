from argparse import Namespace
from pathlib import Path
import sys
from denc import (
    dlogger
)
from hytils import is_access_granted, lightcyan, red


def generate_output_filepath(args: Namespace, suffix: str = "_out") -> Path:
    # return output filepath
    #   priority: `output` -> `out_dir` -> none

    in_fp: Path = Path(args.input).resolve()

    output: str = args.output
    output_dir: str = args.out_dir
    append_params: bool = args.append_params
    if output:
        output_fp: Path = Path(output).resolve()
    elif output_dir:
        output_fp: Path = Path(output_dir).resolve() / in_fp.name
    else:
        output_fp: Path = in_fp.parent / f"{in_fp.stem}{suffix}{in_fp.suffix}"
        append_params = False

    if append_params:
        output_fp: Path = output_fp.parent / f"{output_fp.stem}{suffix}{output_fp.suffix}"

    if output_fp == in_fp:
        dlogger.error(red(f"Error: Output file must not be the input file"))
        sys.exit()

    dlogger.info(f"{lightcyan(f"Output file:")} {output_fp}")
    out_dir: Path = output_fp.parent
    if not is_access_granted(out_dir, 'w'):
        dlogger.error(red(f"Error: no write access to {out_dir}"))
        sys.exit()

    return output_fp
