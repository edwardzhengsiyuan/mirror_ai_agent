from __future__ import annotations

from pathlib import Path

from mingshu.job_service import MingshuJobService
from web_server import create_app


def _fake_runner(job_id, payload, job_dir: Path, progress):
    assert payload["birthplace"] == "上海市"
    assert payload["locale"] in {"zh-CN", "ja"}
    progress(40, "生成章节")
    downloads = job_dir / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    names = {
        "spreads": f"mirror-{job_id}-spreads.pdf",
        "a5": f"mirror-{job_id}-a5.pdf",
    }
    for filename in names.values():
        (downloads / filename).write_bytes(b"%PDF-1.4\n%%EOF\n")
    return {
        "title": "测试命书",
        "spread_count": 1,
        "a5_page_count": 1,
        "downloads": names,
    }


def test_mingshu_job_api_generates_and_downloads(tmp_path) -> None:
    service = MingshuJobService(tmp_path / "jobs", _fake_runner)
    app = create_app(
        storage_root=str(tmp_path / "storage"),
        mingshu_job_service=service,
    )
    client = app.test_client()
    response = client.post(
        "/api/mingshu/jobs",
        json={
            "name": "示例命主",
            "birth": {
                "year": 1995,
                "month": 6,
                "day": 9,
                "hour": 12,
                "minute": 0,
            },
            "birthplace": "上海市",
            "gender": "female",
            "calendar": "solar",
            "locale": "ja",
        },
    )
    assert response.status_code == 202
    job_id = response.get_json()["job"]["id"]
    terminal = service.wait(job_id)
    assert terminal is not None
    assert terminal["status"] == "succeeded"
    assert terminal["progress"] == 100
    assert terminal["request"]["locale"] == "ja"

    response = client.get(f"/api/mingshu/jobs/{job_id}")
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["downloads"]["a5"].endswith("format=a5")
    assert payload["job"]["result"]["title"] == "测试命书"

    response = client.get(f"/api/mingshu/jobs/{job_id}/download?format=a5")
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert response.headers["Content-Disposition"].startswith("attachment;")


def test_mingshu_job_api_rejects_incomplete_birth_data(tmp_path) -> None:
    service = MingshuJobService(tmp_path / "jobs", _fake_runner)
    app = create_app(
        storage_root=str(tmp_path / "storage"),
        mingshu_job_service=service,
    )
    response = app.test_client().post(
        "/api/mingshu/jobs",
        json={
            "birth": {"year": 1995, "month": 2, "day": 31, "hour": 12},
            "birthplace": "",
            "gender": "female",
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "invalid_birth"


def test_mingshu_job_api_rejects_unsupported_locale(tmp_path) -> None:
    service = MingshuJobService(tmp_path / "jobs", _fake_runner)
    app = create_app(
        storage_root=str(tmp_path / "storage"),
        mingshu_job_service=service,
    )
    response = app.test_client().post(
        "/api/mingshu/jobs",
        json={
            "birth": {"year": 1995, "month": 6, "day": 9, "hour": 12},
            "birthplace": "上海市",
            "gender": "female",
            "locale": "fr",
        },
    )
    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "unsupported_locale"
