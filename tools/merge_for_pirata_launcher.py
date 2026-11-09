Import("env")

import os
import shutil
import subprocess


def _is_t_deck_plus_environment() -> bool:
    env_name = env.get("PIOENV", "")
    return env_name.startswith("ttgo_t_deck_plus_")


def _bootloader_offset_for_chip(chip: str) -> str:
    if chip == "esp32s3":
        return "0x0000"
    return "0x1000"


def _merge_for_pirata_launcher(source, target, _env=None, **kwargs):
    if not _is_t_deck_plus_environment():
        return

    build_dir = env.subst("$BUILD_DIR")
    bootloader = os.path.join(build_dir, "bootloader.bin")
    partitions = os.path.join(build_dir, "partitions.bin")
    firmware = os.path.join(build_dir, "firmware.bin")
    merged = os.path.join(build_dir, "pirata_launcher.bin")
    project_dir = env.subst("$PROJECT_DIR")
    env_name = env.get("PIOENV", "unknown_env")
    export_dir = os.path.join(project_dir, "installer", "pirata_launcher")
    exported = os.path.join(export_dir, f"pirata_launcher_{env_name}.bin")

    required_inputs = [bootloader, partitions, firmware]
    missing = [path for path in required_inputs if not os.path.isfile(path)]
    if missing:
        print("[pirata-launcher] Skipping merge, missing input files:")
        for path in missing:
            print(f"  - {path}")
        return

    chip = env.subst("$BOARD_MCU").lower() or "esp32"
    flash_size = env.BoardConfig().get("upload.flash_size", "8MB")
    esptoolpy_dir = env.PioPlatform().get_package_dir("tool-esptoolpy")
    esptool_py = os.path.join(esptoolpy_dir, "esptool.py") if esptoolpy_dir else ""

    if not esptool_py or not os.path.isfile(esptool_py):
        raise RuntimeError("tool-esptoolpy not found in PlatformIO packages")

    cmd = [
        env.subst("$PYTHONEXE"),
        esptool_py,
        "--chip",
        chip,
        "merge_bin",
        "-o",
        merged,
        "--flash_mode",
        "dio",
        "--flash_freq",
        "40m",
        "--flash_size",
        flash_size,
        _bootloader_offset_for_chip(chip),
        bootloader,
        "0x8000",
        partitions,
        "0x10000",
        firmware,
    ]

    print("[pirata-launcher] Merging bootloader + partitions + firmware")
    print(f"[pirata-launcher] Output: {merged}")

    try:
        subprocess.check_call(cmd)
    except subprocess.CalledProcessError as exc:
        print(f"[pirata-launcher] Merge failed with exit code {exc.returncode}")
        raise

    os.makedirs(export_dir, exist_ok=True)
    shutil.copyfile(merged, exported)
    print(f"[pirata-launcher] Exported: {exported}")


def _merge_post_action(target, source, env_kw=None, **kwargs):
    _merge_for_pirata_launcher(source, target, _env=env_kw)


env.AddPostAction("$BUILD_DIR/${PROGNAME}.bin", _merge_post_action)