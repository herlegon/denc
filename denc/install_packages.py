import logging
from pathlib import Path
from pprint import pprint
import signal
import sys
import tomllib
from typing import Any

from hytils import lightcyan, lightgreen, red

sys.path.append(str(Path(__file__).resolve().parent.parent))
from hinstall import (
    parse_config_,
    ExtPackages,
    download_install_ext_packages,
    ilog,
)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    ilog.setLevel(logging.INFO)

    config_fp = (Path(__file__).parent / f"packages.toml").resolve()
    # print(f"loading config: {config_fp}")
    with open(config_fp, "rb") as f:
        data: dict[str, Any] = tomllib.load(f)

    # print(lightcyan(" ".join (("-" * 40, "Parsed TOML", "-" * 40))))
    packages_cfg = parse_config_(data)
    # pprint(packages_cfg)


    external_packages = ExtPackages(packages_cfg, sys.platform)
    # print(lightcyan(" ".join (("-" * 40, "External packages", "-" * 40))))
    # pprint(external_packages)

    # All except python
    packages_to_install = (
        external_packages
        # .get_all_except('python')
        .filter_by_variant(variants=["", "lgpl"])
    )
    # print(lightcyan(" ".join (("-" * 40, f"{sys.platform}, to install", "-" * 40))))
    # pprint(packages_to_install)
    # print()



    if packages_to_install:
        installed: bool = download_install_ext_packages(
            packages=packages_to_install,
            reinstall=False,
            threads=1,
            use_local_rehost=False,
        )
        if installed:
            print(lightgreen("All packages installed"))
        else:
            print(red("Error: missing package(s)"))
    else:
        print(lightgreen("No packages to install"))

