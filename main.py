#!/usr/bin/env python3
"""Application entry point, diagnostics, logging, and single-instance guard."""

import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import tempfile


_MUTEX_HANDLE = None


def configure_logging():
    from app_paths import LOG_DIR

    os.makedirs(str(LOG_DIR), exist_ok=True)
    log_path = os.path.join(str(LOG_DIR), "application.log")
    handler = RotatingFileHandler(
        log_path,
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

    def log_unhandled(exc_type, exc_value, exc_traceback):
        logging.getLogger(__name__).critical(
            "Unhandled application error",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = log_unhandled
    return log_path


def acquire_single_instance():
    """Use a per-session Windows mutex; return False for a duplicate launch."""
    global _MUTEX_HANDLE
    if not sys.platform.startswith("win"):
        return True

    import ctypes

    kernel32 = ctypes.windll.kernel32
    _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, "Local\\BatteryRequisitionApp")
    if not _MUTEX_HANDLE:
        return True
    if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(
            None,
            "โปรแกรมเปิดอยู่แล้ว กรุณาใช้หน้าต่างเดิม",
            "ระบบออกใบเบิกจ่ายแบตเตอรี่",
            0x40,
        )
        kernel32.CloseHandle(_MUTEX_HANDLE)
        _MUTEX_HANDLE = None
        return False
    return True


def release_single_instance():
    global _MUTEX_HANDLE
    if _MUTEX_HANDLE and sys.platform.startswith("win"):
        import ctypes

        ctypes.windll.kernel32.CloseHandle(_MUTEX_HANDLE)
        _MUTEX_HANDLE = None


def run_self_test():
    """Exercise packaged resources, SQLite, Thai PDF shaping, and Excel export."""
    with tempfile.TemporaryDirectory(prefix="battery-requisition-test-") as temp_dir:
        os.environ["BATTERY_REQUISITION_DATA_DIR"] = os.path.join(temp_dir, "data")
        os.environ["BATTERY_REQUISITION_DOCUMENTS_DIR"] = os.path.join(
            temp_dir, "documents"
        )

        from database.db import DB_FILE, init_db, validate_database
        from services.pdf_generator import generate_requisition_pdf
        from services.report_export import export_requisitions_to_excel

        init_db()
        validate_database(DB_FILE)

        pdf_path = generate_requisition_pdf(
            {
                "req_no": "SELF-TEST-0001",
                "req_date": "01/01/2026",
                "driver_name": "ทดสอบระบบ",
                "vehicle_plate": "TEST",
                "customer_name": "ทดสอบภาษาไทย",
            },
            [
                {
                    "item_name": "แบตเตอรี่ทดสอบภาษาไทย 50 Ah",
                    "quantity": 1,
                    "unit": "ลูก",
                }
            ],
            output_path=os.path.join(temp_dir, "self-test.pdf"),
        )
        report_path = export_requisitions_to_excel(
            [
                {
                    "req_no": "SELF-TEST-0001",
                    "req_date": "01/01/2026",
                    "vehicle_plate": "TEST",
                    "driver_name": "ทดสอบระบบ",
                    "customer_name": "ทดสอบภาษาไทย",
                    "total_units": 1,
                    "status": "COMPLETED",
                }
            ],
            filter_desc="Self test",
            output_path=os.path.join(temp_dir, "self-test.xlsx"),
        )
        if not os.path.isfile(pdf_path) or os.path.getsize(pdf_path) == 0:
            raise RuntimeError("PDF self-test failed")
        if not os.path.isfile(report_path) or os.path.getsize(report_path) == 0:
            raise RuntimeError("Excel self-test failed")
    return 0


def initialize_user_data():
    """Initialize and validate the real per-user database without opening the UI."""
    configure_logging()
    from database.db import DB_FILE, init_db, validate_database

    init_db()
    validate_database(DB_FILE)
    return 0


def main():
    if "--self-test" in sys.argv:
        return run_self_test()
    if "--initialize-only" in sys.argv:
        return initialize_user_data()

    configure_logging()
    if not acquire_single_instance():
        return 0

    try:
        from ui.app import BatteryRequisitionApp

        app = BatteryRequisitionApp()
        app.mainloop()
    except Exception:
        logging.getLogger(__name__).exception("Application startup failed")
        if sys.platform.startswith("win"):
            try:
                import ctypes

                ctypes.windll.user32.MessageBoxW(
                    None,
                    "ไม่สามารถเปิดโปรแกรมได้ กรุณาส่งไฟล์ log ให้ผู้ดูแลระบบ",
                    "ระบบออกใบเบิกจ่ายแบตเตอรี่",
                    0x10,
                )
            except Exception:
                pass
        return 1
    finally:
        release_single_instance()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
