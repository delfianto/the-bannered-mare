"""Tests for shared service-layer helpers — the unified `apply_update` (BE-H5).

`apply_update` is the single partial-update mechanism. Its own null policy is
fixed and consistent: every key present in the patch (that is editable) is set,
an explicit ``None`` clears. The *caller* decides what goes in the patch, so a
"clearable" endpoint (profile) passes None to clear, while a "skip-on-None"
endpoint drops None keys first — both routed through one helper.
"""

from src.core.base_service import apply_update
from src.core.persistence import Preset

_EDITABLE = {"name", "description", "is_default"}


def test_present_values_are_set_absent_keys_untouched() -> None:
    preset = Preset(name="Old", description="old desc", is_default=False)

    apply_update(preset, {"name": "New", "is_default": True}, _EDITABLE)

    assert preset.name == "New"
    assert preset.is_default is True
    assert preset.description == "old desc"  # key absent from patch → untouched


def test_explicit_none_clears_the_field() -> None:
    preset = Preset(name="Keep", description="had a description")

    apply_update(preset, {"description": None}, _EDITABLE)

    assert preset.description is None  # present key with None → cleared
    assert preset.name == "Keep"


def test_non_editable_keys_are_ignored() -> None:
    """A key outside the editable allow-list is not written (over-posting defense)."""
    preset = Preset(name="Keep")

    apply_update(preset, {"name": "Changed", "id": "hacked", "bogus": 1}, _EDITABLE)

    assert preset.name == "Changed"
    assert preset.id != "hacked"


def test_skip_on_none_pattern_never_clears() -> None:
    """Skip-on-None services drop None from the patch, so None cannot clear a field."""
    preset = Preset(name="Keep", description="keep desc")

    provided = {"name": None, "description": "updated"}
    patch = {k: v for k, v in provided.items() if v is not None}
    apply_update(preset, patch, _EDITABLE)

    assert preset.name == "Keep"  # None dropped from the patch → not cleared
    assert preset.description == "updated"
