from pathlib import Path
import re
import unittest

from app_paths import APP_VERSION


ROOT = Path(__file__).resolve().parents[1]


class ReleaseConfigurationTests(unittest.TestCase):
    def test_release_version_is_consistent(self):
        installer = (ROOT / "installer.iss").read_text(encoding="utf-8-sig")
        workflow = (ROOT / ".github/workflows/build-windows.yml").read_text(
            encoding="utf-8"
        )
        version_info = (ROOT / "version_info.txt").read_text(encoding="utf-8")

        self.assertIn(f'#define MyAppVersion "{APP_VERSION}"', installer)
        self.assertIn(f"BatteryRequisition_Setup_v{APP_VERSION}.exe", workflow)
        self.assertIn(f'StringStruct("FileVersion", "{APP_VERSION}")', version_info)
        self.assertIn(f'StringStruct("ProductVersion", "{APP_VERSION}")', version_info)

    def test_windows_payloads_and_thai_installer_are_configured(self):
        installer = (ROOT / "installer.iss").read_text(encoding="utf-8-sig")
        workflow = (ROOT / ".github/workflows/build-windows.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn('matrix:\n        architecture: [x86, x64]', workflow)
        self.assertIn('Source: "dist_x86\\BatteryRequisition\\*"', installer)
        self.assertIn('Source: "dist_x64\\BatteryRequisition\\*"', installer)
        self.assertIn('MessagesFile: "compiler:Languages\\Thai.isl"', installer)
        self.assertIn("MinVersion=6.1sp1", installer)
        self.assertIn("ArchitecturesAllowed=x86os or x64os", installer)

    def test_all_dependency_versions_are_exactly_pinned(self):
        for filename in ("requirements.txt", "requirements-build.txt"):
            lines = (ROOT / filename).read_text(encoding="utf-8").splitlines()
            requirements = [
                line.strip()
                for line in lines
                if line.strip() and not line.lstrip().startswith(("#", "-r "))
            ]
            for requirement in requirements:
                self.assertRegex(requirement, r"^[A-Za-z0-9_.-]+==[^=<>!~]+$")

    def test_spec_bundles_catalog_fonts_and_thai_shaping(self):
        spec = (ROOT / "app.spec").read_text(encoding="utf-8")

        self.assertRegex(spec, re.compile(r"\('assets',\s*'assets'\)"))
        self.assertIn("('รุ่นแบตเตอรี่.xlsx', '.')", spec)
        self.assertIn("'uharfbuzz'", spec)
        self.assertIn("version='version_info.txt'", spec)


if __name__ == "__main__":
    unittest.main()
