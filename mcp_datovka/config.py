"""Configuration - loads box credentials from environment variables."""

import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PRODUCTION_BASE_URL = "https://ws1.mojedatovaschranka.cz"
TEST_BASE_URL = "https://ws1.czebox.cz"


@dataclass
class BoxConfig:
    alias: str
    box_id: str
    username: str
    password: str


def is_test_env() -> bool:
    return os.environ.get("DATOVKA_TEST_ENV", "false").lower() == "true"


def get_base_url() -> str:
    return TEST_BASE_URL if is_test_env() else PRODUCTION_BASE_URL


def get_soap_urls() -> dict[str, str]:
    base = get_base_url()
    return {
        "operations": f"{base}/DS/dz",
        "info": f"{base}/DS/dx",
        "search": f"{base}/DS/df",
        "access": f"{base}/DS/DsManage",
    }


def load_boxes() -> list[BoxConfig]:
    """Load box configurations from DATOVKA_BOX_N_* env vars."""
    boxes = []
    for i in range(1, 100):
        alias = os.environ.get(f"DATOVKA_BOX_{i}_ALIAS")
        if alias is None:
            break
        box_id = os.environ.get(f"DATOVKA_BOX_{i}_ID", "")
        username = os.environ.get(f"DATOVKA_BOX_{i}_USERNAME", "")
        password = os.environ.get(f"DATOVKA_BOX_{i}_PASSWORD", "")
        if not username or not password:
            logger.warning(f"Box {alias}: missing credentials, skipping")
            continue
        boxes.append(BoxConfig(alias=alias, box_id=box_id, username=username, password=password))
    if not boxes:
        logger.warning("No boxes configured. Set DATOVKA_BOX_1_ALIAS, etc. in .env")
    return boxes


# Singleton
_boxes: list[BoxConfig] | None = None


def get_boxes() -> list[BoxConfig]:
    global _boxes
    if _boxes is None:
        _boxes = load_boxes()
    return _boxes


def get_box(alias: str) -> BoxConfig | None:
    for box in get_boxes():
        if box.alias == alias:
            return box
    return None
