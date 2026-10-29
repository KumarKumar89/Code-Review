"""Small, validated reader for the versioned model catalogue."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ModelProfile:
    id: str
    family: str
    roles: tuple[str, ...]
    modalities: tuple[str, ...]
    license: str
    resource_tier: str
    recommended_default: bool
    official_url: str
    notes: str


def default_registry_path() -> Path:
    """Resolve model_registry.json relative to the project root."""
    return Path(__file__).resolve().parents[2] / "model_registry.json"


def load_registry(path: str | Path | None = None) -> list[ModelProfile]:
    """Load the catalogue and validate required fields and unique model IDs."""
    registry_path = Path(path) if path is not None else default_registry_path()
    try:
        raw: Any = json.loads(registry_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"Cannot read model registry at {registry_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in model registry {registry_path}: {exc}") from exc

    if not isinstance(raw, list):
        raise ValueError("Model registry root must be a JSON list.")

    profiles: list[ModelProfile] = []
    seen: set[str] = set()
    required = {
        "id", "family", "roles", "modalities", "license",
        "resource_tier", "recommended_default", "official_url", "notes",
    }

    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"Registry item {index} must be an object.")
        missing = required - item.keys()
        if missing:
            raise ValueError(f"Registry item {index} missing fields: {sorted(missing)}")
        model_id = item["id"]
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError(f"Registry item {index} has an invalid id.")
        if model_id in seen:
            raise ValueError(f"Duplicate model id: {model_id}")
        seen.add(model_id)

        for field in ("roles", "modalities"):
            value = item[field]
            if not isinstance(value, list) or not value or not all(
                isinstance(entry, str) and entry.strip() for entry in value
            ):
                raise ValueError(f"{model_id}: '{field}' must be a non-empty list of strings.")

        for field in ("family", "license", "resource_tier", "official_url", "notes"):
            if not isinstance(item[field], str) or not item[field].strip():
                raise ValueError(f"{model_id}: '{field}' must be a non-empty string.")

        if not isinstance(item["recommended_default"], bool):
            raise ValueError(f"{model_id}: recommended_default must be boolean.")
        if not item["official_url"].startswith("https://huggingface.co/"):
            raise ValueError(f"{model_id}: official_url must point to its Hugging Face model card.")

        profiles.append(
            ModelProfile(
                id=model_id,
                family=item["family"],
                roles=tuple(item["roles"]),
                modalities=tuple(item["modalities"]),
                license=item["license"],
                resource_tier=item["resource_tier"],
                recommended_default=item["recommended_default"],
                official_url=item["official_url"],
                notes=item["notes"],
            )
        )

    if profiles and sum(profile.recommended_default for profile in profiles) > 1:
        raise ValueError("At most one model may be marked as the default.")
    return profiles


def get_model(model_id: str, path: str | Path | None = None) -> ModelProfile:
    """Get one model profile by exact Hugging Face repository ID."""
    for profile in load_registry(path):
        if profile.id == model_id:
            return profile
    raise KeyError(f"Unknown model id: {model_id}")


def recommended_default(path: str | Path | None = None) -> ModelProfile:
    """Return the single marked default, or fail clearly if none exists."""
    matches = [profile for profile in load_registry(path) if profile.recommended_default]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one default model, found {len(matches)}.")
    return matches[0]
