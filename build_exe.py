"""Build the canonical PyInstaller payload for the current Python architecture."""

import platform
import sys
import subprocess


def build():
    if not sys.platform.startswith("win"):
        raise SystemExit("ต้องรันการสร้างไฟล์ Windows บน Windows เท่านั้น")

    architecture = "x64" if platform.architecture()[0] == "64bit" else "x86"
    print(f"กำลังสร้าง payload สำหรับ Windows {architecture}")
    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements-build.txt"]
        )

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "app.spec",
        "--clean",
        "-y",
        "--distpath",
        f"dist_{architecture}",
        "--workpath",
        f"build_{architecture}",
    ]
    subprocess.check_call(cmd)
    executable = f"dist_{architecture}\\BatteryRequisition\\BatteryRequisition.exe"
    subprocess.check_call([executable, "--self-test"])
    print(f"สร้างและทดสอบสำเร็จ: {executable}")
    print("Universal Setup ต้องมีทั้ง dist_x86 และ dist_x64 ก่อน compile installer.iss")

if __name__ == "__main__":
    build()
