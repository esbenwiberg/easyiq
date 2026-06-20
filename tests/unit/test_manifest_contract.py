from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = ROOT / "custom_components" / "aula_easyiq"


class ManifestContractTests(unittest.TestCase):
    def test_domain_matches_integration_folder(self) -> None:
        manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text())

        self.assertEqual("aula_easyiq", manifest["domain"])
        self.assertTrue((ROOT / "custom_components" / manifest["domain"]).is_dir())

    def test_runtime_dependencies_cover_imported_third_party_packages(self) -> None:
        manifest = json.loads((INTEGRATION_DIR / "manifest.json").read_text())
        requirements = " ".join(manifest.get("requirements", []))

        for package_name in ("aiohttp", "beautifulsoup4", "lxml", "pytz", "requests"):
            with self.subTest(package_name=package_name):
                self.assertIn(package_name, requirements)

    def test_strings_and_english_translation_share_config_and_options(self) -> None:
        strings = json.loads((INTEGRATION_DIR / "strings.json").read_text())
        english = json.loads((INTEGRATION_DIR / "translations" / "en.json").read_text())

        self.assertEqual(strings["config"], english["config"])
        self.assertEqual(strings["options"], english["options"])


if __name__ == "__main__":
    unittest.main()
