"""Tests for configuration loading."""

import os
import pytest
from unittest.mock import patch

from mcp_datovka.config import BoxConfig, load_boxes, is_test_env, get_base_url, get_soap_urls


class TestBoxConfig:
    def test_dataclass_fields(self):
        box = BoxConfig(alias="test", box_id="abc1234", username="user", password="pass")
        assert box.alias == "test"
        assert box.box_id == "abc1234"
        assert box.username == "user"
        assert box.password == "pass"


class TestLoadBoxes:
    @patch.dict(os.environ, {
        "DATOVKA_BOX_1_ALIAS": "box-a",
        "DATOVKA_BOX_1_ID": "aaa1111",
        "DATOVKA_BOX_1_USERNAME": "user1",
        "DATOVKA_BOX_1_PASSWORD": "pass1",
    }, clear=False)
    def test_load_single_box(self):
        # Clear singleton cache
        import mcp_datovka.config as cfg
        cfg._boxes = None
        boxes = load_boxes()
        assert len(boxes) >= 1
        box = next(b for b in boxes if b.alias == "box-a")
        assert box.box_id == "aaa1111"
        assert box.username == "user1"

    @patch.dict(os.environ, {
        "DATOVKA_BOX_1_ALIAS": "box-a",
        "DATOVKA_BOX_1_ID": "aaa1111",
        "DATOVKA_BOX_1_USERNAME": "user1",
        "DATOVKA_BOX_1_PASSWORD": "pass1",
        "DATOVKA_BOX_2_ALIAS": "box-b",
        "DATOVKA_BOX_2_ID": "bbb2222",
        "DATOVKA_BOX_2_USERNAME": "user2",
        "DATOVKA_BOX_2_PASSWORD": "pass2",
    }, clear=False)
    def test_load_multiple_boxes(self):
        import mcp_datovka.config as cfg
        cfg._boxes = None
        boxes = load_boxes()
        aliases = [b.alias for b in boxes]
        assert "box-a" in aliases
        assert "box-b" in aliases

    @patch.dict(os.environ, {
        "DATOVKA_BOX_1_ALIAS": "incomplete",
        "DATOVKA_BOX_1_ID": "xxx1234",
        # Missing USERNAME and PASSWORD
    }, clear=False)
    def test_skip_box_without_credentials(self):
        import mcp_datovka.config as cfg
        cfg._boxes = None
        # Remove any existing credentials for this box
        env = os.environ.copy()
        env.pop("DATOVKA_BOX_1_USERNAME", None)
        env.pop("DATOVKA_BOX_1_PASSWORD", None)
        with patch.dict(os.environ, env, clear=True):
            boxes = load_boxes()
            incomplete = [b for b in boxes if b.alias == "incomplete"]
            assert len(incomplete) == 0


class TestEnvironment:
    @patch.dict(os.environ, {"DATOVKA_TEST_ENV": "true"}, clear=False)
    def test_is_test_env_true(self):
        assert is_test_env() is True

    @patch.dict(os.environ, {"DATOVKA_TEST_ENV": "false"}, clear=False)
    def test_is_test_env_false(self):
        assert is_test_env() is False

    @patch.dict(os.environ, {}, clear=False)
    def test_is_test_env_default(self):
        os.environ.pop("DATOVKA_TEST_ENV", None)
        assert is_test_env() is False

    @patch.dict(os.environ, {"DATOVKA_TEST_ENV": "true"}, clear=False)
    def test_get_base_url_test(self):
        assert "czebox.cz" in get_base_url()

    @patch.dict(os.environ, {"DATOVKA_TEST_ENV": "false"}, clear=False)
    def test_get_base_url_production(self):
        assert "mojedatovaschranka.cz" in get_base_url()

    @patch.dict(os.environ, {"DATOVKA_TEST_ENV": "false"}, clear=False)
    def test_get_soap_urls_has_all_endpoints(self):
        urls = get_soap_urls()
        assert "operations" in urls
        assert "info" in urls
        assert "search" in urls
        assert "access" in urls
        for url in urls.values():
            assert url.startswith("https://")
