import os
from datetime import datetime
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from database import db
from database.migrations import run_migrations


class DatabaseLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.data_dir = self.root / "active"
        self.backup_dir = self.data_dir / "backups"
        self.db_file = self.data_dir / "inventory.db"
        self.path_patches = [
            patch.object(db, "DATA_DIR", str(self.data_dir)),
            patch.object(db, "BACKUP_DIR", str(self.backup_dir)),
            patch.object(db, "DB_FILE", str(self.db_file)),
        ]
        for path_patch in self.path_patches:
            path_patch.start()

    def tearDown(self):
        for path_patch in reversed(self.path_patches):
            path_patch.stop()
        self.temp_dir.cleanup()

    def _create_app_database(self, path, marker):
        path.parent.mkdir(parents=True, exist_ok=True)
        run_migrations(str(path), backup_dir=str(path.parent / "backups"))
        conn = sqlite3.connect(str(path))
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('marker', ?)",
            (marker,),
        )
        conn.commit()
        conn.close()

    def _marker(self, path=None):
        conn = sqlite3.connect(str(path or self.db_file))
        value = conn.execute(
            "SELECT value FROM settings WHERE key = 'marker'"
        ).fetchone()[0]
        conn.close()
        return value

    def test_fresh_database_seeds_catalog_with_zero_stock(self):
        with patch.object(db, "legacy_database_candidates", return_value=[]):
            result = db.init_db()

        conn = sqlite3.connect(str(self.db_file))
        count, total_stock = conn.execute(
            "SELECT COUNT(*), SUM(stock_qty) FROM items"
        ).fetchone()
        app_version = conn.execute(
            "SELECT value FROM settings WHERE key = 'app_version'"
        ).fetchone()[0]
        conn.close()

        self.assertEqual(count, 385)
        self.assertEqual(total_stock, 0)
        self.assertEqual(app_version, db.APP_VERSION)
        self.assertIsNone(result["migrated_from"])

    def test_legacy_migration_prefers_first_candidate_and_preserves_all(self):
        preferred = self.root / "old-app" / "data" / "inventory.db"
        fallback = self.root / "old-app" / "inventory.db"
        self._create_app_database(preferred, "preferred")
        self._create_app_database(fallback, "fallback")

        with patch.object(
            db, "legacy_database_candidates", return_value=[preferred, fallback]
        ):
            selected = db.migrate_legacy_database()

        self.assertEqual(selected, str(preferred))
        self.assertEqual(self._marker(), "preferred")
        preserved = list((self.backup_dir / "legacy_import").glob("*.db"))
        self.assertEqual(len(preserved), 2)

    def test_restore_validates_and_preserves_current_database(self):
        self._create_app_database(self.db_file, "before")
        backup_path = db.create_backup("manual", str(self.root / "exports"))

        conn = sqlite3.connect(str(self.db_file))
        conn.execute(
            "UPDATE settings SET value='after' WHERE key='marker'"
        )
        conn.commit()
        conn.close()

        result = db.restore_database(backup_path)

        self.assertEqual(self._marker(), "before")
        self.assertTrue(os.path.isfile(result["pre_restore"]))
        self.assertTrue(db.validate_database(str(self.db_file)))

    def test_invalid_restore_file_is_rejected_without_touching_current_data(self):
        self._create_app_database(self.db_file, "safe")
        invalid = self.root / "invalid.db"
        invalid.write_text("not sqlite", encoding="utf-8")

        with self.assertRaises(ValueError):
            db.restore_database(str(invalid))

        self.assertEqual(self._marker(), "safe")

    def test_backup_includes_committed_wal_transactions(self):
        self._create_app_database(self.db_file, "before-wal")
        writer = sqlite3.connect(str(self.db_file))
        writer.execute("PRAGMA journal_mode = WAL")
        writer.execute(
            "UPDATE settings SET value='inside-wal' WHERE key='marker'"
        )
        writer.commit()
        try:
            backup_path = db.create_backup("manual", str(self.root / "exports"))
        finally:
            writer.close()

        self.assertEqual(self._marker(Path(backup_path)), "inside-wal")

    def test_pre_update_backups_keep_latest_ten(self):
        self._create_app_database(self.db_file, "existing")
        conn = sqlite3.connect(str(self.db_file))
        conn.execute(
            "INSERT INTO items "
            "(brand, item_code, item_name, stock_qty) VALUES ('T', 'T-1', 'Test', 0)"
        )
        conn.commit()
        conn.close()

        for patch_number in range(12):
            with patch.object(db, "APP_VERSION", f"test-{patch_number}"):
                db.init_db()

        backups = list(self.backup_dir.glob("inventory_pre_update_*.db"))
        self.assertEqual(len(backups), 10)

    def test_invalid_daily_backup_is_recreated(self):
        self._create_app_database(self.db_file, "daily-source")
        daily_path = self.backup_dir / (
            f"inventory_daily_{datetime.now().strftime('%Y%m%d')}.db"
        )
        daily_path.write_text("broken", encoding="utf-8")

        result = db.daily_auto_backup()

        self.assertEqual(result, str(daily_path))
        self.assertTrue(db.validate_database(str(daily_path)))
        self.assertEqual(self._marker(daily_path), "daily-source")


if __name__ == "__main__":
    unittest.main()
