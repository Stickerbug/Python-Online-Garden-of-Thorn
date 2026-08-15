import ast
import html
import inspect
import re
import unittest
from pathlib import Path
from unittest import mock

import app as gtn


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
API_DOC_PATH = ROOT / "docs" / "API.md"
CARD_DOC_PATH = ROOT / "docs" / "卡牌描述规范.md"


def _normalized_route(path):
    return re.sub(r"<(?:int|path):([^>]+)>", r"<\1>", str(path))


class ApiDocumentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
        cls.doc = html.unescape(API_DOC_PATH.read_text(encoding="utf-8"))

    def test_every_http_api_route_is_listed(self):
        routes = set()
        for node in self.tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "route"
                    and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                ):
                    continue
                path = str(decorator.args[0].value)
                if path.startswith("/api/"):
                    routes.add(_normalized_route(path))
        missing = sorted(path for path in routes if path not in self.doc)
        self.assertEqual(missing, [], f"API.md 缺少 HTTP 路径: {missing}")

    def test_every_client_socket_event_is_listed(self):
        events = set()
        for node in self.tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not (
                    isinstance(decorator, ast.Call)
                    and isinstance(decorator.func, ast.Attribute)
                    and decorator.func.attr == "on"
                    and decorator.args
                    and isinstance(decorator.args[0], ast.Constant)
                ):
                    continue
                events.add(str(decorator.args[0].value))
        missing = sorted(event for event in events if f"<code>{event}</code>" not in self.doc)
        self.assertEqual(missing, [], f"API.md 缺少 Socket.IO 事件: {missing}")

    def test_document_index_and_card_spec_exist(self):
        self.assertTrue(CARD_DOC_PATH.is_file())
        index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
        self.assertIn("API.md", index)
        self.assertIn("卡牌描述规范.md", index)
        self.assertFalse((ROOT / "卡牌描述规范.md").exists())


class ApiSecurityBoundaryTests(unittest.TestCase):
    def setUp(self):
        gtn.app.config.update(TESTING=True)
        self.client = gtn.app.test_client()

    def test_sensitive_content_mutations_have_server_side_guards(self):
        self.assertIn("_require_staff_account_json", inspect.getsource(gtn.api_mods_save))
        self.assertIn("_require_account_json", inspect.getsource(gtn.api_community_mod_validate_url))

    def test_anonymous_content_mutations_are_rejected(self):
        save_response = self.client.post("/api/mods/save", json={"format_version": 2})
        validate_response = self.client.post(
            "/api/community-mods/validate-url",
            json={"public_url": "https://example.invalid/mod.json"},
        )
        self.assertEqual(save_response.status_code, 401)
        self.assertEqual(validate_response.status_code, 401)

    def test_regular_account_cannot_write_builtin_mods(self):
        with (
            mock.patch.object(gtn, "_require_account_json", return_value=(41, "Player", None)),
            mock.patch.object(gtn, "feedback_is_staff", return_value=False),
        ):
            response = self.client.post("/api/mods/save", json={"format_version": 2})
        self.assertEqual(response.status_code, 403)

    def test_detailed_health_is_not_available_through_public_proxy(self):
        response = self.client.get(
            "/api/health/full",
            headers={"X-Forwarded-For": "203.0.113.10"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(response.status_code, 403)

    def test_public_health_remains_available(self):
        response = self.client.get("/api/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
