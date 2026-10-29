import json

import pytest

from reviewer_swarm.registry import get_model, load_registry, recommended_default


def test_default_registry_has_unique_models_and_one_default():
    profiles = load_registry()
    ids = [profile.id for profile in profiles]
    assert len(profiles) >= 5
    assert len(ids) == len(set(ids))
    assert sum(profile.recommended_default for profile in profiles) == 1


def test_default_model_is_lower_resource_coder():
    profile = recommended_default()
    assert profile.id == "Qwen/Qwen2.5-Coder-3B-Instruct"
    assert "code" in profile.modalities


def test_get_model_raises_for_unknown_id():
    with pytest.raises(KeyError):
        get_model("vendor/nonexistent")


def test_registry_rejects_duplicate_ids(tmp_path):
    path = tmp_path / "registry.json"
    valid = {
        "id": "org/model", "family": "family", "roles": ["review"],
        "modalities": ["text"], "license": "license", "resource_tier": "small",
        "recommended_default": False, "official_url": "https://huggingface.co/org/model",
        "notes": "notes",
    }
    path.write_text(json.dumps([valid, valid]), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate model id"):
        load_registry(path)
