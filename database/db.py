import sqlite3
import os
from datetime import datetime
from database.migrations import run_migrations
from app_paths import (
    APP_VERSION,
    BACKUP_DIR as APP_BACKUP_DIR,
    DB_FILE as APP_DB_FILE,
    DATA_DIR as APP_DATA_DIR,
    ensure_app_directories,
    legacy_database_candidates,
    resource_path,
)

DATA_DIR = str(APP_DATA_DIR)
DB_FILE = str(APP_DB_FILE)
BACKUP_DIR = str(APP_BACKUP_DIR)


REQUIRED_TABLES = {"items", "requisitions", "requisition_items", "settings"}


def _safe_reason(reason):
    return "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in reason)


def validate_database(db_path, require_schema=True):
    """Validate that a file is a readable, internally consistent app database."""
    if not os.path.isfile(db_path):
        raise ValueError("ไม่พบไฟล์ฐานข้อมูลที่เลือก")

    try:
        conn = sqlite3.connect(f"file:{os.path.abspath(db_path)}?mode=ro", uri=True)
        integrity = conn.execute("PRAGMA integrity_check;").fetchone()[0]
        if integrity != "ok":
            raise ValueError(f"ฐานข้อมูลไม่สมบูรณ์: {integrity}")
        if require_schema:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            missing = REQUIRED_TABLES - tables
            if missing:
                raise ValueError(
                    "ไฟล์นี้ไม่ใช่ฐานข้อมูลของโปรแกรม (ขาดตาราง: "
                    + ", ".join(sorted(missing))
                    + ")"
                )
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"ไม่สามารถอ่านฐานข้อมูลได้: {exc}") from exc
    finally:
        if "conn" in locals():
            conn.close()
    return True


def _copy_sqlite_database(source_path, destination_path):
    """Copy a live SQLite database without losing committed WAL transactions."""
    source = sqlite3.connect(
        f"file:{os.path.abspath(source_path)}?mode=ro", uri=True, timeout=10.0
    )
    destination = sqlite3.connect(destination_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


def create_backup(reason="manual", destination_folder=None, keep=None):
    """Create a transactionally consistent SQLite backup and apply retention."""
    if not os.path.exists(DB_FILE):
        raise FileNotFoundError("ยังไม่มีฐานข้อมูลให้สำรอง")

    destination_folder = destination_folder or BACKUP_DIR
    os.makedirs(destination_folder, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    prefix = _safe_reason(reason)
    backup_path = os.path.join(
        destination_folder, f"inventory_{prefix}_{timestamp}.db"
    )

    try:
        _copy_sqlite_database(DB_FILE, backup_path)
        validate_database(backup_path)
    except Exception:
        if os.path.exists(backup_path):
            os.remove(backup_path)
        raise
    if keep is not None:
        retention_prefix = (
            "inventory_pre_update_" if prefix.startswith("pre_update_")
            else f"inventory_{prefix}_"
        )
        _prune_backups(destination_folder, retention_prefix, keep)
    return os.path.abspath(backup_path)


def _prune_backups(folder, prefix, keep):
    matches = sorted(
        (
            os.path.join(folder, name)
            for name in os.listdir(folder)
            if name.startswith(prefix) and name.endswith(".db")
        ),
        key=os.path.getmtime,
        reverse=True,
    )
    for old_path in matches[max(0, keep):]:
        try:
            os.remove(old_path)
        except OSError:
            pass


def migrate_legacy_database():
    """Migrate the preferred old DB and preserve every discovered candidate."""
    if os.path.exists(DB_FILE):
        return None

    candidates = [path for path in legacy_database_candidates() if path.is_file()]
    if not candidates:
        return None

    os.makedirs(DATA_DIR, exist_ok=True)
    legacy_backup_dir = os.path.join(BACKUP_DIR, "legacy_import")
    os.makedirs(legacy_backup_dir, exist_ok=True)
    valid_candidates = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    for index, candidate in enumerate(candidates, start=1):
        try:
            validate_database(str(candidate))
        except ValueError:
            continue
        valid_candidates.append(candidate)
        preserved = os.path.join(
            legacy_backup_dir,
            f"legacy_candidate_{index}_{timestamp}_{candidate.name}",
        )
        try:
            _copy_sqlite_database(str(candidate), preserved)
            validate_database(preserved)
        except Exception:
            if os.path.exists(preserved):
                os.remove(preserved)
            valid_candidates.pop()

    if not valid_candidates:
        return None

    # Candidate order prefers {app}/data/inventory.db, as agreed with the user.
    try:
        _copy_sqlite_database(str(valid_candidates[0]), DB_FILE)
        validate_database(DB_FILE)
    except Exception:
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        raise
    return str(valid_candidates[0])


def ensure_data_directory():
    """
    ตรวจสอบและสร้างโฟลเดอร์ data/ พร้อมย้าย inventory.db เดิมมายัง data/inventory.db
    เพื่อให้ข้อมูลปลอดภัยจากการถูกเขียนทับเวลาอัปเดตโค้ดหรือแตกไฟล์ทับ
    """
    ensure_app_directories()
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(BACKUP_DIR, exist_ok=True)
    return migrate_legacy_database()


def daily_auto_backup():
    """
    สำรองฐานข้อมูลอัตโนมัติวันละ 1 ครั้งเมื่อเปิดโปรแกรม
    บันทึกเป็น database_backups/auto_daily_YYYYMMDD.db
    """
    if not os.path.exists(DB_FILE):
        return None

    today_str = datetime.now().strftime("%Y%m%d")
    daily_backup_path = os.path.join(BACKUP_DIR, f"inventory_daily_{today_str}.db")

    if os.path.exists(daily_backup_path):
        try:
            validate_database(daily_backup_path)
            return daily_backup_path
        except ValueError:
            try:
                os.remove(daily_backup_path)
            except OSError:
                return None

    try:
        _copy_sqlite_database(DB_FILE, daily_backup_path)
        validate_database(daily_backup_path)
        _prune_backups(BACKUP_DIR, "inventory_daily_", 30)
        print(f"[*] Daily safety snapshot created: {daily_backup_path}")
        return daily_backup_path
    except Exception as e:
        if os.path.exists(daily_backup_path):
            try:
                os.remove(daily_backup_path)
            except OSError:
                pass
        print(f"[!] Warning: Daily backup failed: {e}")
        return None


def get_connection():
    ensure_data_directory()
    conn = sqlite3.connect(DB_FILE, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


def _existing_database_metadata():
    """Read update metadata before any migration changes the database."""
    try:
        conn = sqlite3.connect(
            f"file:{os.path.abspath(DB_FILE)}?mode=ro", uri=True, timeout=10.0
        )
        previous_version_row = conn.execute(
            "SELECT value FROM settings WHERE key = 'app_version'"
        ).fetchone()
        has_data = conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] > 0
        return (
            previous_version_row[0] if previous_version_row else None,
            has_data,
        )
    except sqlite3.DatabaseError:
        return None, False
    finally:
        if "conn" in locals():
            conn.close()


def init_db():
    database_existed = os.path.exists(DB_FILE)
    migrated_from = ensure_data_directory()

    if database_existed and not migrated_from:
        previous_version, has_data = _existing_database_metadata()
        if has_data and previous_version != APP_VERSION:
            create_backup(
                reason=f"pre_update_{previous_version or 'unknown'}_to_{APP_VERSION}",
                keep=10,
            )

    # 1. รันระบบ Migration ตรวจสอบและอัปเกรดโครงสร้างตารางอัตโนมัติ
    run_migrations(DB_FILE, backup_dir=BACKUP_DIR)

    conn = get_connection()
    cursor = conn.cursor()

    # ค่าเริ่มต้นสำหรับงานคลังแบตเตอรี่
    default_settings = [
        ("company_name", "บริษัท คลังแบตเตอรี่และบริการ จำกัด"),
        ("slip_title", "ใบเบิกและจ่ายสินค้าขึ้นรถส่งของ (BATTERY LOADING & DELIVERY SLIP)"),
        ("sign_role_1", "พนักงานขับรถ / ผู้รับของขึ้นรถ"),
        ("sign_role_2", "เจ้าหน้าที่จัดจ่ายคลังสินค้า"),
        ("sign_role_3", "ผู้อนุมัติ / หัวหน้าคลัง"),
    ]
    for k, v in default_settings:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # ถ้ายังไม่มีข้อมูลสินค้า และมีไฟล์ รุ่นแบตเตอรี่.xlsx ให้นำเข้าข้อมูลจริงอัตโนมัติ
    cursor.execute("SELECT COUNT(*) as count FROM items")
    excel_path = str(resource_path("รุ่นแบตเตอรี่.xlsx"))
    if cursor.fetchone()["count"] == 0 and os.path.exists(excel_path):
        conn.commit()
        conn.close()
        try:
            from import_excel import import_batteries
            import_batteries(excel_path=excel_path, db_path=DB_FILE, default_qty=0)
        except Exception as e:
            print(f"[!] Excel import note: {e}")
        conn = get_connection()
        cursor = conn.cursor()

    conn.commit()
    conn.close()

    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('app_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (APP_VERSION,),
    )
    conn.commit()
    conn.close()
    daily_auto_backup()
    return {"database": DB_FILE, "migrated_from": migrated_from}


def restore_database(backup_path):
    """Validate and restore a database after preserving the current state."""
    validate_database(backup_path)
    pre_restore = create_backup(reason="pre_restore", keep=10)
    temp_path = DB_FILE + ".restore_tmp"

    for sidecar in (temp_path, temp_path + "-wal", temp_path + "-shm"):
        if os.path.exists(sidecar):
            os.remove(sidecar)

    source = sqlite3.connect(f"file:{os.path.abspath(backup_path)}?mode=ro", uri=True)
    destination = sqlite3.connect(temp_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    validate_database(temp_path)
    for sidecar in (DB_FILE + "-wal", DB_FILE + "-shm"):
        if os.path.exists(sidecar):
            os.remove(sidecar)
    os.replace(temp_path, DB_FILE)
    run_migrations(DB_FILE, backup_dir=BACKUP_DIR)
    return {"restored_from": os.path.abspath(backup_path), "pre_restore": pre_restore}


def generate_next_req_no():
    """สร้างเลขที่ใบเบิกอัตโนมัติ เช่น REQ-202609-0001"""
    now = datetime.now()
    prefix = f"REQ-{now.strftime('%Y%m')}-"
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT req_no FROM requisitions 
        WHERE req_no LIKE ? 
        ORDER BY id DESC LIMIT 1
    """, (f"{prefix}%",))
    row = cursor.fetchone()
    conn.close()

    if row:
        last_num = int(row["req_no"].split("-")[-1])
        next_num = last_num + 1
    else:
        next_num = 1

    return f"{prefix}{next_num:04d}"


if __name__ == "__main__":
    init_db()
    print("Battery Database initialized successfully.")
    print("Database path:", DB_FILE)
    print("Next sample req no:", generate_next_req_no())
