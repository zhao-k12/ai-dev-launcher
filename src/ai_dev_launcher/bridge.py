"""JSON bridge used by trusted local desktop clients."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from ai_dev_launcher.config import ConfigStore, default_config_dir
from ai_dev_launcher.errors import LauncherError
from ai_dev_launcher.services import (
    LaunchService,
    ProjectPreparationService,
    ProjectService,
    ToolDetectionService,
)


def _service() -> ProjectService:
    configured = os.environ.get("AI_DEV_CONFIG_DIR")
    config_dir = Path(configured) if configured else default_config_dir()
    return ProjectService(ConfigStore(config_dir))


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    """Execute one project-management request."""

    action = request.get("action")
    payload = request.get("payload") or {}
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    service = _service()
    if action == "projects.list":
        config = service.store.load()
        return {
            "projects": [project.to_dict() for project in service.list_projects()],
            "default_project": config.default_project,
        }
    if action == "projects.add":
        project = service.add_project(
            str(payload.get("name", "")),
            Path(str(payload.get("path", ""))),
        )
        if payload.get("make_default"):
            service.set_default(project.name)
        return {"project": project.to_dict()}
    if action == "projects.default":
        project = service.set_default(str(payload.get("name", "")))
        return {"project": project.to_dict()}
    if action == "projects.remove":
        project = service.remove_project(str(payload.get("name", "")))
        return {"project": project.to_dict()}
    if action == "tools.status":
        results = ToolDetectionService().check_all()
        return {"tools": [result.to_dict() for result in results]}
    if action == "projects.launch":
        project = service.get_project(str(payload.get("name", "")))
        launcher = LaunchService()
        plan = launcher.build_plan(project, use_headroom=True)
        process_id = (
            0
            if os.environ.get("AI_DEV_BRIDGE_TEST_MODE") == "1"
            else launcher.start(plan)
        )
        return {"pid": process_id, "plan": plan.to_dict()}
    if action == "projects.prepare":
        project = service.get_project(str(payload.get("name", "")))
        result = ProjectPreparationService().prepare(
            project,
            dry_run=bool(payload.get("dry_run", False)),
            initialize_git=bool(payload.get("initialize_git", True)),
        )
        return result.to_dict()
    raise ValueError(f"Unknown bridge action: {action}")


def main() -> int:
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ValueError("request must be an object")
        response = {"ok": True, "data": handle_request(request)}
    except (LauncherError, OSError, ValueError, json.JSONDecodeError) as exc:
        response = {"ok": False, "error": str(exc)}
    json.dump(response, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
