"""
Unit tests for repository analyzer (languages, frameworks, file tree).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.repository.analyzer import (
    analyze_repository,
    detect_file_language,
    detect_frameworks_and_tools,
    is_ignored_file,
)


def test_detect_file_language():
    assert detect_file_language(Path("main.py")) == "Python"
    assert detect_file_language(Path("App.tsx")) == "TypeScript"
    assert detect_file_language(Path("index.js")) == "JavaScript"
    assert detect_file_language(Path("Dockerfile")) == "Dockerfile"
    assert detect_file_language(Path("docker-compose.yml")) == "Docker Compose"
    assert detect_file_language(Path("unknown.xyz")) is None


def test_is_ignored_file(tmp_path):
    assert is_ignored_file(tmp_path / ".git" / "config", tmp_path) is True
    assert is_ignored_file(tmp_path / "node_modules" / "express" / "index.js", tmp_path) is True
    assert is_ignored_file(tmp_path / "image.png", tmp_path) is True
    assert is_ignored_file(tmp_path / "app.py", tmp_path) is False
    assert is_ignored_file(tmp_path / "src" / "index.ts", tmp_path) is False


@pytest.mark.asyncio
async def test_analyze_python_repository(tmp_path):
    """Test analyzer on a simulated Python FastAPI repository."""
    # Setup mock repository files
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()\n")
    (tmp_path / "app" / "models.py").write_text("from pydantic import BaseModel\nclass Item(BaseModel):\n    pass\n")
    (tmp_path / "requirements.txt").write_text("fastapi==0.115.0\nuvicorn==0.32.0\npytest==8.3.0\n")
    (tmp_path / "Dockerfile").write_text("FROM python:3.12-slim\n")

    analysis = await analyze_repository(tmp_path)

    assert analysis.primary_language == "Python"
    assert "Python" in analysis.languages
    assert analysis.file_count >= 4
    assert analysis.has_docker is True

    # Framework detection
    fw_names = [f.name for f in analysis.frameworks]
    assert "FastAPI" in fw_names
    assert "pytest" in analysis.test_frameworks
    assert "pip" in analysis.package_managers

    # Summary
    assert "FastAPI" in analysis.summary
    assert "Python" in analysis.summary


@pytest.mark.asyncio
async def test_analyze_node_repository(tmp_path):
    """Test analyzer on a simulated React/Express repository."""
    pkg_data = {
        "name": "sample-app",
        "dependencies": {
            "express": "^4.19.0",
            "react": "^18.3.0",
        },
        "devDependencies": {
            "vitest": "^2.0.0",
            "tailwindcss": "^3.4.0",
        },
    }
    (tmp_path / "package.json").write_text(json.dumps(pkg_data))
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "server.ts").write_text("import express from 'express';\nconst app = express();\n")
    (tmp_path / "src" / "App.tsx").write_text("export function App() { return <div>Hello</div>; }\n")

    analysis = await analyze_repository(tmp_path)

    assert analysis.primary_language == "TypeScript"
    fw_names = [f.name for f in analysis.frameworks]
    assert "Express" in fw_names
    assert "React" in fw_names
    assert "TailwindCSS" in fw_names
    assert "vitest" in analysis.test_frameworks
    assert "npm" in analysis.package_managers
