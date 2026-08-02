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
    RuntimeService,
    PrivateToolUpdateService,
    WorkspaceService,
    ToolDetectionService,
)


def _service() -> ProjectService:
    configured = os.environ.get("AI_DEV_CONFIG_DIR")
    config_dir = Path(configured) if configured else default_config_dir()
    return ProjectService(ConfigStore(config_dir))


def _config_dir() -> Path:
    configured = os.environ.get("AI_DEV_CONFIG_DIR")
    return Path(configured) if configured else default_config_dir()


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
    if action == "projects.create":
        project = service.create_project(
            str(payload.get("name", "")),
            Path(str(payload.get("parent", ""))),
        )
        return {"project": project.to_dict()}
    if action == "projects.default":
        project = service.set_default(str(payload.get("name", "")))
        return {"project": project.to_dict()}
    if action == "projects.update":
        project, old_path, moved = service.update_project(
            str(payload.get("current_name", "")),
            str(payload.get("name", "")),
            Path(str(payload.get("parent", ""))),
        )
        return {"project": project.to_dict(), "old_path": old_path, "moved": moved}
    if action == "projects.remove":
        project = service.remove_project(str(payload.get("name", "")))
        return {"project": project.to_dict()}
    if action == "tools.status":
        results = ToolDetectionService().check_all()
        return {"tools": [result.to_dict() for result in results]}
    if action == "runtime.bootstrap":
        return RuntimeService(_config_dir()).bootstrap()
    if action == "runtime.status":
        return RuntimeService(_config_dir()).status()
    if action == "runtime.update":
        if os.environ.get("AI_DEV_BRIDGE_TEST_MODE") == "1":
            return {"tools": [], "skipped": "test mode"}
        return PrivateToolUpdateService(_config_dir()).update_all()
    if action == "projects.launch":
        project = service.get_project(str(payload.get("name", "")))
        launcher = LaunchService(
            private_tool_root=_config_dir() / "runtime" / "tools"
        )
        plan = launcher.build_plan(project, use_headroom=True)
        process_id = (
            0
            if os.environ.get("AI_DEV_BRIDGE_TEST_MODE") == "1"
            else launcher.start(plan)
        )
        return {"pid": process_id, "plan": plan.to_dict()}
    if action == "chat.plan":
        project = service.get_project(str(payload.get("name", "")))
        prompt = str(payload.get("prompt", "")).strip()
        if not prompt:
            raise ValueError("Chat prompt cannot be empty")
        permission = str(payload.get("permission", "standard"))
        session_id = str(payload.get("session_id", "")).strip()
        images = payload.get("images") or []
        if not isinstance(images, list) or not all(isinstance(path, str) for path in images):
            raise ValueError("Chat images must be a list of paths")
        image_args: list[str] = []
        for image in images:
            image_path = Path(image)
            if not image_path.is_file():
                raise ValueError(f"Chat image does not exist: {image}")
            image_args.extend(["--image", str(image_path)])
        args: list[str] = ["exec"]
        if session_id:
            args.append("resume")
            if permission == "full":
                args.append("--dangerously-bypass-approvals-and-sandbox")
            else:
                args.extend(["--config", 'sandbox_mode="workspace-write"'])
            args.append("--json")
            args.extend(image_args)
            args.append(session_id)
        else:
            args.extend(["--json", "--color", "never"])
            if permission == "full":
                args.append("--dangerously-bypass-approvals-and-sandbox")
            else:
                args.extend(["--sandbox", "workspace-write"])
            args.extend(image_args)
        # Always stream the prompt through stdin. Passing Chinese or long prompts as a
        # positional Windows argument is unreliable once Headroom wraps Codex.
        args.append("-")
        launcher = LaunchService(private_tool_root=_config_dir() / "runtime" / "tools")
        return launcher.build_plan(project, use_headroom=True, codex_args=tuple(args)).to_dict()
    if action.startswith("workspace."):
        project = service.get_project(str(payload.get("name", "")))
        workspace = WorkspaceService(project)
        if action == "workspace.tree":
            return workspace.tree()
        if action == "workspace.read":
            return workspace.read(str(payload.get("path", "")))
        if action == "workspace.images":
            return workspace.recent_images(float(payload.get("since", 0)), int(payload.get("limit", 16)))
        if action == "workspace.image-path":
            return workspace.image_path(str(payload.get("path", "")))
        if action == "workspace.image-paths":
            paths = payload.get("paths", [])
            if not isinstance(paths, list) or not all(isinstance(path, str) for path in paths):
                raise ValueError("Image paths must be a list of strings")
            return workspace.image_paths(paths)
        if action == "workspace.diff":
            path = payload.get("path")
            return workspace.git_diff(str(path) if path else None)
        if action == "workspace.stage":
            return workspace.stage(str(payload.get("path", "")))
        if action == "workspace.restore":
            return workspace.restore(str(payload.get("path", "")))
        if action == "workspace.terminal":
            return workspace.run_terminal(str(payload.get("command", "")))
        if action == "workspace.stats":
            return workspace.headroom_stats(int(payload.get("port", 8787)))
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
    # Keep the Electron bridge byte stream ASCII-only so Windows code pages cannot
    # corrupt Chinese status labels emitted by the packaged executable.
    json.dump(response, sys.stdout, ensure_ascii=True)
    sys.stdout.write("\n")
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
