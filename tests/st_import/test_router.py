"""HTTP tests for POST /api/presets/import."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.st_import.factories import preset_dict, st_marker, st_prompt

_URL = "/api/presets/import"
_REFS_PRESET_DIR = Path(__file__).resolve().parents[2] / "refs" / "preset"
_SAMPLE_DIR = Path(__file__).resolve().parents[1] / "preset" / "sample"
_SAMPLES = sorted(_SAMPLE_DIR.glob("*.json"))


def _upload(body: bytes | str, filename: str = "preset.json") -> dict:
    payload = body.encode("utf-8") if isinstance(body, str) else body
    return {"file": (filename, payload, "application/json")}


def _valid_body(**kw) -> str:
    return json.dumps(
        preset_dict(
            [
                st_prompt("main", system_prompt=True, content="Be {{char}}."),
                st_prompt("rules", content="Follow the rules."),
                st_marker("chatHistory"),
            ],
            ["main", "rules", "chatHistory"],
            **kw,
        )
    )


class TestImportEndpoint:
    def test_201_prompts_only(self, client: TestClient) -> None:
        resp = client.post(_URL, files=_upload(_valid_body(), "Adventure.json"))
        assert resp.status_code == 201
        data = resp.json()
        assert data["template_name"] == "Adventure"
        assert isinstance(data["fragment_ids"], list)
        assert len(data["fragment_ids"]) == 1
        assert data["preset_id"] is None
        assert isinstance(data["warnings"], list)

    def test_201_with_samplers_sets_preset_id(self, client: TestClient) -> None:
        resp = client.post(
            _URL, files=_upload(_valid_body(samplers={"temperature": 0.9}), "WithSamplers.json")
        )
        assert resp.status_code == 201
        assert resp.json()["preset_id"] is not None

    def test_400_invalid_json(self, client: TestClient) -> None:
        resp = client.post(_URL, files=_upload(b"{not json", "broken.json"))
        assert resp.status_code == 400
        assert "JSON" in resp.json()["detail"]

    def test_400_text_completion_preset(self, client: TestClient) -> None:
        body = json.dumps({"temp": 0.7, "rep_pen": 1.1, "instruct": {}})
        resp = client.post(_URL, files=_upload(body, "textgen.json"))
        assert resp.status_code == 400
        assert "text-completion" in resp.json()["detail"]

    def test_400_wrong_extension(self, client: TestClient) -> None:
        resp = client.post(_URL, files=_upload(_valid_body(), "preset.png"))
        assert resp.status_code == 400
        assert ".json" in resp.json()["detail"]

    def test_400_regex_script(self, client: TestClient) -> None:
        body = json.dumps({"findRegex": "/x/", "replaceString": "y"})
        resp = client.post(_URL, files=_upload(body, "regex.json"))
        assert resp.status_code == 400

    def test_400_empty_file(self, client: TestClient) -> None:
        resp = client.post(_URL, files=_upload(b"", "empty.json"))
        assert resp.status_code == 400

    def test_422_missing_file(self, client: TestClient) -> None:
        resp = client.post(_URL)
        assert resp.status_code == 422

    @pytest.mark.skipif(
        not _REFS_PRESET_DIR.exists() or not list(_REFS_PRESET_DIR.glob("*.json")),
        reason="no local refs/preset/*.json reference files",
    )
    def test_imports_real_reference_preset(self, client: TestClient) -> None:
        sample = sorted(_REFS_PRESET_DIR.glob("*.json"))[0]
        resp = client.post(_URL, files=_upload(sample.read_bytes(), sample.name))
        assert resp.status_code == 201
        data = resp.json()
        assert data["template_id"]
        assert isinstance(data["warnings"], list)


class TestCommittedSamples:
    """Import the checked-in funny sample presets in tests/preset/sample/."""

    @pytest.mark.parametrize("sample", _SAMPLES, ids=lambda p: p.name)
    def test_sample_imports(self, client: TestClient, sample: Path) -> None:
        resp = client.post(_URL, files=_upload(sample.read_bytes(), sample.name))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["template_id"]
        assert isinstance(data["warnings"], list)

    def test_chef_sample_creates_preset_with_samplers(self, client: TestClient) -> None:
        sample = _SAMPLE_DIR / "chef_dungeon_master.json"
        data = client.post(_URL, files=_upload(sample.read_bytes(), sample.name)).json()
        assert data["preset_id"] is not None
        assert data["template_name"] == "chef_dungeon_master"

    def test_freaky_sample_is_prompts_only(self, client: TestClient) -> None:
        sample = _SAMPLE_DIR / "freaky_frankenpurr.json"
        data = client.post(_URL, files=_upload(sample.read_bytes(), sample.name)).json()
        assert data["preset_id"] is None  # no sampler block
        assert len(data["fragment_ids"]) == 5  # 2 disabled toggles are skipped

    def test_minimal_sample_has_no_fragments(self, client: TestClient) -> None:
        sample = _SAMPLE_DIR / "minimal_greeter.json"
        data = client.post(_URL, files=_upload(sample.read_bytes(), sample.name)).json()
        assert data["fragment_ids"] == []
