from concurrent.futures import ThreadPoolExecutor
import logging
import multiprocessing
from pathlib import Path
from pprint import pformat, pprint
import signal
import sys
import time
import tomllib
from typing import Any

from hytils import lightcyan, lightgreen, red

sys.path.append(str(Path(__file__).resolve().parent.parent))
from hinstall import (
    parse_config_,
    ExtPackages,
    download_install_ext_packages,
    ilog,
    PyPackages,
    PyPackage,
    g_backend_dirs,
)

def main():
    ilog.setLevel(logging.INFO)

    config_fp = (Path(__file__).parent / f"packages.toml").resolve()
    with open(config_fp, "rb") as f:
        data: dict[str, Any] = tomllib.load(f)

    packages_cfg = parse_config_(data)

    # Update backend directories: no isolated python exe
    g_backend_dirs.python_exe = sys.executable
    ilog.debug(pformat(g_backend_dirs))


    # External packages
    external_packages = ExtPackages(packages_cfg, sys.platform)
    packages_to_install = (
        external_packages
        # .get_all_except('python')
        .filter_by_variant(variants=["", "lgpl"])
    )

    if packages_to_install:
        installed: bool = download_install_ext_packages(
            packages=packages_to_install,
            reinstall=False,
            threads=1,
            use_local_rehost=False,
        )
        if installed:
            ilog.info(lightgreen("All external packages installed"))
        else:
            raise SystemError(red("Error: missing package(s)"))
    else:
        ilog.warning(lightgreen("No packages to install"))


    # ilog.setLevel(logging.DEBUG)


    # Python Packages
    ilog.info(lightgreen("Install additionnal python packages"))
    keep_up_to_date: bool = True
    py_packages = PyPackages(
        packages_cfg,
        sys.platform,
        keep_up_to_date=keep_up_to_date
    )
    # Delayed packages are installed in a second time because the full version of hinstall
    # had to install common python package in its own environment.
    # here, python is not in a separated environment
    delayed_pkgs = py_packages.get_delayed()

    # hsys was installed in the fisrt round
    from hsys import is_feature_supported

    cuda = is_feature_supported('cuda')
    tensorrt = is_feature_supported('tensorrt')
    directml = is_feature_supported('directml')
    rocm = is_feature_supported('rocm')

    execution_providers = [
        f"CUDA: {'✅' if cuda else '❌'}",
        f"TensorRT: {'✅' if tensorrt else '❌'}",
        f"direct ML: {'✅' if directml else '❌'}",
        f"RocM: {'✅' if rocm else '❌'}",
    ]
    ilog.info(f"Supported execution providers\n  " + "\n  ".join(execution_providers))
    start_time = time.time()

    for pkg in py_packages.get_by_execution_provider('cuda'):
        pkg.skip = not cuda
        pkg.supported = cuda

    for pkg in py_packages.get_by_execution_provider('rocm'):
        pkg.skip = not rocm
        pkg.supported = rocm

    for pkg in py_packages.get_by_execution_provider('directml'):
        pkg.skip = not directml
        pkg.supported = directml

    cpu_fallback = all([x is False for x in (cuda, tensorrt, rocm)])
    for pkg in py_packages.get_by_execution_provider('cpu'):
        pkg.skip = not cpu_fallback
        pkg.supported = cpu_fallback


    ilog.info("Supported packages:")
    supported_pkgs = py_packages.get_delayed(supported_only=True)
    for pkg in supported_pkgs:
        ilog.info(lightcyan(pkg.pretty_name))
        ilog.debug(pformat(pkg))

    cpu_count = multiprocessing.cpu_count()
    cpu_count = max(cpu_count - 1, int(cpu_count * 4 / 5))
    with ThreadPoolExecutor(max_workers=max(1, min(cpu_count, len(supported_pkgs)))) as executor:
        executor.map(lambda pkg: pkg.update_info(), supported_pkgs)
    elapsed = time.time() - start_time


    for pkg in supported_pkgs:
        pkg: PyPackage
        pkg_info = [
            f"{lightcyan(pkg.name)}:\n    latest version: {pkg.latest_version}\n    selected: {pkg.version}",
            f"      installed: {pkg.installed}",
            f"      variant: {pkg.variant}",
            f"      wheel: {pkg.wheel}",
            f"      wheel url: {pkg.wheel_url}",
            f"      size: {pkg.size // 1024}kB",
            f"      do cache: {pkg.do_cache}"
        ]
        ilog.debug("\n".join(pkg_info))
    ilog.debug(f" package versions updated in {elapsed:.02f}s")


    # To install
    uninstalled_pkgs = supported_pkgs.get_delayed().get_not_installed()
    packages_to_install_str = [lightcyan(f"{pkg.name} ({pkg.version})") for pkg in uninstalled_pkgs]
    if uninstalled_pkgs:
        ilog.info("Packages to install: " + ", ".join(packages_to_install_str))
    else:
        ilog.info(lightgreen("All python packages installed"))
        return


    # Download if packages have to be cached
    for pkg in supported_pkgs:
        if pkg.installed or not pkg.do_cache:
            continue
        start_time = time.time()
        downloaded = pkg.download_wheel(force=False, use_pip=False)
        elapsed = time.time() - start_time
        ilog.info(f"{pkg.name} downloaded in {elapsed:.02f}s")

    # Install packages
    for pkg in uninstalled_pkgs:
        pkg.install(reinstall=False)


    py_packages.update_installed_versions()
    uninstalled_pkgs = supported_pkgs.get_delayed().get_not_installed()
    if not uninstalled_pkgs:
        for pkg in uninstalled_pkgs:
            ilog.critical(f"{pkg.name} not installed")
            pkg.install(recover=True)
    else:
        ilog.info(lightgreen("All python packages installed"))



if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    main()
