"""Stable resource and user-data locations for source and frozen builds."""

from __future__ import annotations

import os
import sys
from pathlib import Path


APP_ID = "BatteryRequisition"
APP_DISPLAY_NAME = "ระบบออกใบเบิกจ่ายแบตเตอรี่"
APP_VERSION = "1.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent
IS_FROZEN = bool(getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"))
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT)).resolve()
EXECUTABLE_DIR = (
    Path(sys.executable).resolve().parent if IS_FROZEN else PROJECT_ROOT
)


def _windows_documents_dir() -> Path:
    """Return the configured Windows Documents folder, including redirected folders."""
    try:
        import ctypes

        buffer = ctypes.create_unicode_buffer(260)
        # CSIDL_PERSONAL works on Windows 7 and newer.
        result = ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer)
        if result == 0 and buffer.value:
            return Path(buffer.value)
    except (AttributeError, OSError):
        pass
    return Path.home() / "Documents"


def _default_data_dir() -> Path:
    override = os.environ.get("BATTERY_REQUISITION_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if IS_FROZEN and sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / APP_ID
        return Path.home() / "AppData" / "Local" / APP_ID
    return PROJECT_ROOT / "data"


def _default_documents_dir() -> Path:
    override = os.environ.get("BATTERY_REQUISITION_DOCUMENTS_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform.startswith("win"):
        return _windows_documents_dir() / APP_ID
    return PROJECT_ROOT


DATA_DIR = _default_data_dir()
DB_FILE = DATA_DIR / "inventory.db"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR = DATA_DIR / "logs"

DOCUMENTS_DIR = _default_documents_dir()
PDF_DIR = DOCUMENTS_DIR / "PDF" if IS_FROZEN else PROJECT_ROOT / "output_pdfs"
REPORT_DIR = (
    DOCUMENTS_DIR / "Reports" if IS_FROZEN else PROJECT_ROOT / "exported_reports"
)


def resource_path(*parts: str) -> Path:
    return RESOURCE_DIR.joinpath(*parts)


def ensure_app_directories() -> None:
    for path in (DATA_DIR, BACKUP_DIR, LOG_DIR, PDF_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def legacy_database_candidates() -> list[Path]:
    """Return old DB locations in priority order without returning the active DB."""
    if not IS_FROZEN:
        return []

    local_appdata = Path(os.environ.get("LOCALAPPDATA", EXECUTABLE_DIR.parent))
    program_files = Path(os.environ.get("ProgramFiles", EXECUTABLE_DIR.parent))
    program_files_x86 = Path(os.environ.get("ProgramFiles(x86)", program_files))
    candidates = [
        EXECUTABLE_DIR / "data" / "inventory.db",
        EXECUTABLE_DIR / "inventory.db",
        RESOURCE_DIR / "data" / "inventory.db",
        local_appdata / "Programs" / "RequisitionApp" / "data" / "inventory.db",
        local_appdata / "Programs" / "RequisitionApp" / "inventory.db",
        program_files / "RequisitionApp" / "data" / "inventory.db",
        program_files / "RequisitionApp" / "inventory.db",
        program_files_x86 / "RequisitionApp" / "data" / "inventory.db",
        program_files_x86 / "RequisitionApp" / "inventory.db",
        Path.cwd() / "data" / "inventory.db",
        Path.cwd() / "inventory.db",
    ]
    active = DB_FILE.resolve()
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved == active or resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique
