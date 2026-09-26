import os
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


def _load_env_file(env_path: Optional[str] = None) -> None:
    path = env_path or os.path.join(os.path.dirname(__file__), "..", ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value  # preserve explicit environment overrides


_load_env_file()


def _deep_get(d: dict, path: str, default=None):
    keys = path.split("__")
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return default
    return d if d is not None else default


def _default_app_data_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "SnaglistPro"
    return Path.home() / ".snaglistpro"


def _build_default_database_url() -> str:
    database_dir = _default_app_data_dir()
    db_path = database_dir / "data" / "snaglist.db"
    return f"sqlite:///{db_path.as_posix()}"


def _resolve_database_url(database_url: Optional[str]) -> str:
    if not database_url:
        return _build_default_database_url()
    if os.name != "nt" or not database_url.startswith("sqlite"):
        return database_url

    candidate = database_url.replace("sqlite:///", "", 1).replace("sqlite://", "", 1)
    candidate = candidate.replace("/", "\\")
    if "Program Files" in candidate or "program files" in candidate:
        return _build_default_database_url()
    return database_url


@dataclass
class Settings:
    project_default_facility: str = ""
    project_default_client: str = ""
    project_default_floor: str = ""
    project_default_priority: str = "Medium"
    project_default_status: str = "Open"
    project_output_dir: str = ""

    categories_normalize: Dict[str, str] = field(default_factory=lambda: {
        "hvac": "Hvac", "electrical": "Electrical", "interior": "Interior",
        "fire safety": "Fire Safety", "fire": "Fire Safety",
        "network": "Network", "network/it": "Network",
        "furniture": "Furniture", "cleaning": "Cleaning",
        "plumbing": "Plumbing", "civil": "Civil",
        "doors/windows": "Interior", "rodent entry point": "Rodent entry point",
        "parking": "Parking", "signages": "Signages",
        "landscapping": "Landscapping", "service": "Service",
        "electrical hod": "Electrical HOD", "hvac hod": "Hvac HOD",
        "fire safety hod": "Fire Safety HOD", "network hod": "Network HOD",
        "unassigned": "Unassigned",
    })

    vendors: Dict[str, str] = field(default_factory=lambda: {
        "Electrical": "Ever green", "Hvac": "Apel (Carrier)",
        "HVAC": "Apel (Carrier)", "Network": "Nikhita",
        "Fire Safety": "V3 automation", "Fire": "V3 automation",
        "Furniture": "Imported & Featherlite",
    })

    vendor_overrides: Dict[str, str] = field(default_factory=dict)

    priority_high_keywords: List[str] = field(default_factory=lambda: [
        "critical", "urgent", "leak", "fire", "smoke",
        "short circuit", "hazard", "not working", "broken",
        "water leak", "immediately",
    ])

    images_resize_size: int = 200
    images_quality: int = 90
    checklist_default_path: str = ""

    database_url: str = field(default_factory=_build_default_database_url)

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    notify_email: str = ""

    ai_enabled: bool = True
    ai_provider: str = "ollama"
    ollama_url: str = "http://localhost:11434"
    ollama_text_model: str = "llama3.2"
    ai_request_timeout: int = 120
    max_ai_calls_per_run: int = 1000

    def __post_init__(self):
        env_overrides = {k: v for k, v in os.environ.items() if k.startswith("SNAGLIST__")}
        for env_key, env_val in env_overrides.items():
            path = env_key.replace("SNAGLIST__", "").lower()
            parts = path.split("__")
            obj = self
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current = getattr(obj, part, None)
                    if isinstance(current, list):
                        setattr(obj, part, [x.strip() for x in env_val.split(",")])
                    elif isinstance(current, bool):
                        setattr(obj, part, env_val.lower() in ("1", "true", "yes", "on"))
                    elif isinstance(current, int):
                        setattr(obj, part, int(env_val))
                    else:
                        setattr(obj, part, env_val)
                else:
                    pass

    def get_vendor(self, category: str) -> str:
        if not category:
            return ""
        for key, vendor in self.vendors.items():
            if key.lower() == category.lower():
                return vendor
        return ""

    def normalize_category(self, category: str) -> str:
        cat_lower = category.lower().strip()
        return self.categories_normalize.get(cat_lower, category)

    def is_high_priority(self, description: str) -> bool:
        desc_lower = description.lower()
        for kw in self.priority_high_keywords:
            if kw in desc_lower:
                return True
        return False

def _load_config_yaml() -> dict:
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "config.yaml"),
        os.path.join(os.path.dirname(__file__), "..", "config.yml"),
    ]
    for path in paths:
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
    return {}


def _build_settings() -> Settings:
    raw = _load_config_yaml()
    kwargs = {}

    flat_map = {
        "project.default_facility": "project_default_facility",
        "project.default_client": "project_default_client",
        "project.default_floor": "project_default_floor",
        "project.default_priority": "project_default_priority",
        "project.default_status": "project_default_status",
        "project.output_dir": "project_output_dir",
        "images.resize_size": "images_resize_size",
        "images.quality": "images_quality",
        "database.url": "database_url",
    }

    for yaml_path, attr in flat_map.items():
        val = _deep_get(raw, yaml_path.replace(".", "__"))
        if val is not None:
            kwargs[attr] = val

    if "categories" in raw and "normalize" in raw["categories"]:
        kwargs["categories_normalize"] = raw["categories"]["normalize"]
    if "vendors" in raw:
        kwargs["vendors"] = raw["vendors"]
    if "vendor_overrides" in raw:
        kwargs["vendor_overrides"] = raw["vendor_overrides"]
    if "priority" in raw and "high_keywords" in raw["priority"]:
        kwargs["priority_high_keywords"] = raw["priority"]["high_keywords"]

    default_database_url = _build_default_database_url()
    kwargs["database_url"] = _resolve_database_url(
        os.environ.get("DATABASE_URL") or kwargs.get("database_url", default_database_url)
    )

    kwargs["smtp_host"] = os.environ.get("SMTP_HOST") or ""
    kwargs["smtp_port"] = int(os.environ.get("SMTP_PORT") or "587")
    kwargs["smtp_user"] = os.environ.get("SMTP_USER") or ""
    kwargs["smtp_pass"] = os.environ.get("SMTP_PASS") or ""
    kwargs["notify_email"] = os.environ.get("NOTIFY_EMAIL") or ""

    kwargs["ai_enabled"] = os.environ.get("AI_ENABLED", "true").lower() not in ("0", "false", "no")
    kwargs["ai_provider"] = os.environ.get("AI_PROVIDER", "ollama")
    kwargs["ollama_url"] = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    kwargs["ollama_text_model"] = os.environ.get("OLLAMA_TEXT_MODEL", "llama3.2")
    kwargs["ai_request_timeout"] = int(os.environ.get("AI_REQUEST_TIMEOUT", "120"))
    kwargs["max_ai_calls_per_run"] = int(os.environ.get("MAX_AI_CALLS_PER_RUN", "1000"))

    return Settings(**kwargs)


settings = _build_settings()
