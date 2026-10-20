import json
from pathlib import Path
from typing import NotRequired, TypedDict, cast

import httpx

from market_sdk.errors import UserInputError

ZERO_BYTES32 = "0x0000000000000000000000000000000000000000000000000000000000000000"


class SiteConfig(TypedDict):
    site_url: str
    builder_mode: bool
    geoblock: bool
    builder_code: str
    order_metadata: str


class GeoblockStatus(TypedDict):
    blocked: bool
    country: NotRequired[str]
    region: NotRequired[str]


DEFAULT_SITE_CONFIG: SiteConfig = {
    "site_url": "",
    "builder_mode": False,
    "geoblock": False,
    "builder_code": "",
    "order_metadata": ZERO_BYTES32,
}


def _config_path() -> Path:
    package_path = Path(__file__).resolve()
    candidates = (
        Path.cwd() / ".sdk" / "site-config.json",
        package_path.parent.parent / ".sdk" / "site-config.json",
        package_path.parent.parent.parent / ".sdk" / "site-config.json",
    )
    return next((path for path in candidates if path.exists()), candidates[0])


def _read_string(config: dict[str, object], field: str) -> str:
    value = config.get(field, DEFAULT_SITE_CONFIG.get(field))
    if not isinstance(value, str):
        raise RuntimeError(f".sdk/site-config.json field {field} must be a string")
    return value


def _read_bool(config: dict[str, object], field: str) -> bool:
    value = config.get(field, DEFAULT_SITE_CONFIG.get(field))
    if not isinstance(value, bool):
        raise RuntimeError(f".sdk/site-config.json field {field} must be a boolean")
    return value


def _load_site_config() -> SiteConfig:
    path = _config_path()
    if not path.exists():
        return DEFAULT_SITE_CONFIG.copy()

    try:
        parsed: object = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"Unable to read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Invalid {path}: {error}") from error

    if not isinstance(parsed, dict):
        raise RuntimeError(f"Invalid {path}: expected a JSON object")
    config = cast(dict[str, object], parsed)

    return {
        "site_url": _read_string(config, "site_url"),
        "builder_mode": _read_bool(config, "builder_mode"),
        "geoblock": _read_bool(config, "geoblock"),
        "builder_code": _read_string(config, "builder_code"),
        "order_metadata": _read_string(config, "order_metadata"),
    }


SITE_CONFIG = _load_site_config()

GEOBLOCK_HOST = "https://geoblock.kuest.com"


def get_site_order_context() -> dict[str, str]:
    context: dict[str, str] = {}
    builder_code = SITE_CONFIG["builder_code"].strip()
    if SITE_CONFIG["builder_mode"] and (not builder_code or builder_code == ZERO_BYTES32):
        raise ValueError("builder_mode requires a non-zero builder_code in .sdk/site-config.json")
    if builder_code:
        context["builder_code"] = builder_code
    metadata = SITE_CONFIG["order_metadata"].strip()
    if metadata and metadata != ZERO_BYTES32:
        context["metadata"] = metadata
    return context


def _geoblock_site_url() -> str:
    site_url = SITE_CONFIG["site_url"].strip()
    if not site_url:
        raise UserInputError("site_url must be configured when geoblock is enabled")
    return site_url


def _parse_geoblock_status(value: object) -> GeoblockStatus:
    if not isinstance(value, dict):
        raise RuntimeError("invalid geoblock response")
    record = cast(dict[str, object], value)
    blocked = record.get("blocked")
    if not isinstance(blocked, bool):
        raise RuntimeError("invalid geoblock response")
    country = record.get("country")
    region = record.get("region")
    return {
        "blocked": blocked,
        "country": country if isinstance(country, str) else "unknown",
        "region": region if isinstance(region, str) else "unknown",
    }


def fetch_geoblock_status() -> GeoblockStatus:
    response = httpx.get(GEOBLOCK_HOST, params={"url": _geoblock_site_url()}, timeout=10)
    response.raise_for_status()
    return _parse_geoblock_status(response.json())


async def async_fetch_geoblock_status() -> GeoblockStatus:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(GEOBLOCK_HOST, params={"url": _geoblock_site_url()})
    response.raise_for_status()
    return _parse_geoblock_status(response.json())


def ensure_geoblock_allowed(status: GeoblockStatus) -> None:
    if status["blocked"]:
        raise UserInputError(
            "trading blocked for configured site_url ({}) in {}, {}".format(
                SITE_CONFIG["site_url"],
                status.get("country", "unknown"),
                status.get("region", "unknown"),
            )
        )
