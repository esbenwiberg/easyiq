from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INTEGRATION_DIR = ROOT / "custom_components" / "aula_easyiq"


class HomeAssistantView:
    requires_auth = True


homeassistant_module = types.ModuleType("homeassistant")
components_module = types.ModuleType("homeassistant.components")
http_module = types.ModuleType("homeassistant.components.http")
core_module = types.ModuleType("homeassistant.core")
aiohttp_module = types.ModuleType("aiohttp")
web_module = types.ModuleType("aiohttp.web")
custom_components_module = types.ModuleType("custom_components")
aula_easyiq_module = types.ModuleType("custom_components.aula_easyiq")

http_module.HomeAssistantView = HomeAssistantView
core_module.HomeAssistant = object
web_module.Request = object
web_module.Response = object
web_module.json_response = lambda *args, **kwargs: (args, kwargs)
aiohttp_module.web = web_module

sys.modules.setdefault("homeassistant", homeassistant_module)
sys.modules.setdefault("homeassistant.components", components_module)
sys.modules.setdefault("homeassistant.components.http", http_module)
sys.modules.setdefault("homeassistant.core", core_module)
sys.modules.setdefault("aiohttp", aiohttp_module)
sys.modules.setdefault("aiohttp.web", web_module)
custom_components_module.__path__ = [str(ROOT / "custom_components")]
aula_easyiq_module.__path__ = [str(INTEGRATION_DIR)]
sys.modules.setdefault("custom_components", custom_components_module)
sys.modules.setdefault("custom_components.aula_easyiq", aula_easyiq_module)


def load_module(name: str, filename: str):
    sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(name, INTEGRATION_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


load_module("custom_components.aula_easyiq.const", "const.py")
load_module("custom_components.aula_easyiq.mitid_auth", "mitid_auth.py")
views = load_module("custom_components.aula_easyiq.views", "views.py")


class MitIDAuthViewTests(unittest.TestCase):
    def test_external_auth_views_do_not_require_home_assistant_login(self) -> None:
        self.assertFalse(views.MitIDAuthStatusView.requires_auth)
        self.assertFalse(views.MitIDAuthCompleteView.requires_auth)


if __name__ == "__main__":
    unittest.main()
