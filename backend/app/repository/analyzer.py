"""
Deep repository structure and codebase intelligence analyzer.

Responsibilities:
- Recursively inspect files while strictly ignoring non-code artifacts and secrets.
- Detect programming languages, calculate Lines of Code (LOC), and compute statistics.
- Detect frameworks, ORMs, libraries, package managers, and test runners.
- Identify Docker, CI/CD, and infrastructure configuration.
- Generate a hierarchical FileTreeNode tree for UI navigation.
- Produce a structured architectural repository summary.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.repository import FileTreeNode, FrameworkInfo, LanguageStat

logger = get_logger(__name__)
settings = get_settings()

# Directories to strictly ignore
IGNORED_DIRECTORIES = frozenset({
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "env",
    "ENV",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    ".output",
    "dist",
    "build",
    "coverage",
    "htmlcov",
    ".idea",
    ".vscode",
    "target",
    "bin",
    "obj",
    "vendor",
    "postgres-data",
    ".gemini",
})

# Extensions to strictly ignore as binary or non-source assets
BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp", ".bmp", ".tiff",
    ".pdf", ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".iso",
    ".pyc", ".pyo", ".pyd", ".class", ".jar", ".war",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".db", ".sqlite", ".sqlite3",
})

# Extension to language mapping
EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "Python",
    ".pyi": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".mts": "TypeScript",
    ".cts": "TypeScript",
    ".html": "HTML",
    ".htm": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sass": "SASS",
    ".less": "LESS",
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown",
    ".markdown": "Markdown",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".ps1": "PowerShell",
    ".sql": "SQL",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".cpp": "C++",
    ".cxx": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".swift": "Swift",
    ".dockerfile": "Dockerfile",
}

SPECIAL_FILENAMES: dict[str, str] = {
    "Dockerfile": "Dockerfile",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "Makefile": "Makefile",
    "Jenkinsfile": "Jenkinsfile",
    "CMakeLists.txt": "CMake",
    ".env.example": "Configuration",
}


class RepositoryAnalysis:
    """Complete analysis representation of a repository codebase."""

    def __init__(
        self,
        languages: dict[str, LanguageStat],
        primary_language: str,
        frameworks: list[FrameworkInfo],
        package_managers: list[str],
        test_frameworks: list[str],
        has_docker: bool,
        has_ci_cd: bool,
        file_count: int,
        total_loc: int,
        total_size_bytes: int,
        file_tree: FileTreeNode,
        all_relative_paths: list[str],
        summary: str,
    ) -> None:
        self.languages = languages
        self.primary_language = primary_language
        self.frameworks = frameworks
        self.package_managers = package_managers
        self.test_frameworks = test_frameworks
        self.has_docker = has_docker
        self.has_ci_cd = has_ci_cd
        self.file_count = file_count
        self.total_loc = total_loc
        self.total_size_bytes = total_size_bytes
        self.file_tree = file_tree
        self.all_relative_paths = all_relative_paths
        self.summary = summary

    def to_dict(self) -> dict[str, Any]:
        return {
            "languages": {k: v.model_dump() for k, v in self.languages.items()},
            "primary_language": self.primary_language,
            "frameworks": [f.model_dump() for f in self.frameworks],
            "package_managers": self.package_managers,
            "test_frameworks": self.test_frameworks,
            "has_docker": self.has_docker,
            "has_ci_cd": self.has_ci_cd,
            "file_count": self.file_count,
            "total_loc": self.total_loc,
            "total_size_bytes": self.total_size_bytes,
            "summary": self.summary,
        }


def detect_file_language(path: Path) -> Optional[str]:
    """Identify the language of a single file."""
    if path.name in SPECIAL_FILENAMES:
        return SPECIAL_FILENAMES[path.name]
    suffix = path.suffix.lower()
    return EXTENSION_LANGUAGE_MAP.get(suffix)


def is_ignored_file(path: Path, root_path: Path) -> bool:
    """Determine if a file should be ignored during indexing and analysis."""
    # Check if any parent folder is ignored
    try:
        rel_parts = path.relative_to(root_path).parts
    except ValueError:
        rel_parts = path.parts

    for part in rel_parts[:-1]:
        if part in IGNORED_DIRECTORIES or part.startswith("."):
            if part not in (".github",):  # Allow .github workflows inspection
                return True

    filename = path.name
    suffix = path.suffix.lower()

    if filename.startswith(".") and filename not in (".env.example", ".gitignore"):
        return True

    if suffix in BINARY_EXTENSIONS:
        return True

    # Ignore secrets / keys
    if suffix in (".pem", ".key", ".p12", ".pfx", ".secret"):
        return True

    return False


def count_file_loc(path: Path) -> int:
    """Safely count non-empty lines of code in a file."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for line in f if line.strip())
    except Exception:
        return 0


def build_file_tree_node(path: Path, root_path: Path) -> Optional[FileTreeNode]:
    """Recursively construct a FileTreeNode for navigation."""
    if is_ignored_file(path, root_path):
        return None

    try:
        rel_path = str(path.relative_to(root_path)).replace("\\", "/")
    except ValueError:
        rel_path = path.name

    if path.is_file():
        size = path.stat().st_size
        lang = detect_file_language(path)
        return FileTreeNode(
            name=path.name,
            path=rel_path,
            is_dir=False,
            size_bytes=size,
            extension=path.suffix.lower() or None,
            language=lang,
            children=None,
        )

    if path.is_dir():
        if path.name in IGNORED_DIRECTORIES and path != root_path:
            return None

        children: list[FileTreeNode] = []
        try:
            for entry in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                child_node = build_file_tree_node(entry, root_path)
                if child_node is not None:
                    children.append(child_node)
        except (PermissionError, FileNotFoundError):
            pass

        return FileTreeNode(
            name=path.name if path != root_path else root_path.name,
            path=rel_path if path != root_path else "",
            is_dir=True,
            size_bytes=sum(c.size_bytes for c in children),
            children=children,
        )

    return None


def detect_frameworks_and_tools(root_path: Path) -> tuple[list[FrameworkInfo], list[str], list[str], bool, bool]:
    """
    Inspect manifest and config files across the repository to detect:
    - Frameworks & libraries
    - Package managers
    - Test runners
    - Docker & CI/CD presence
    """
    frameworks: list[FrameworkInfo] = []
    package_managers: set[str] = set()
    test_frameworks: set[str] = set()
    has_docker = False
    has_ci_cd = False

    # 1. Docker checks
    if (root_path / "Dockerfile").exists() or any(root_path.glob("**/Dockerfile")):
        has_docker = True
    if (root_path / "docker-compose.yml").exists() or (root_path / "docker-compose.yaml").exists():
        has_docker = True

    # 2. CI/CD checks
    if (root_path / ".github" / "workflows").is_dir():
        has_ci_cd = True

    # 3. Python Ecosystem (requirements.txt, pyproject.toml, setup.py, Pipfile)
    req_files = list(root_path.glob("**/requirements*.txt"))
    pyproject_files = list(root_path.glob("**/pyproject.toml"))
    setup_files = list(root_path.glob("**/setup.py"))
    pipfile_files = list(root_path.glob("**/Pipfile"))

    py_contents: list[str] = []
    for f in req_files + pyproject_files + setup_files + pipfile_files:
        if not is_ignored_file(f, root_path):
            try:
                py_contents.append(f.read_text(encoding="utf-8", errors="ignore").lower())
            except Exception:
                pass

    if pyproject_files:
        package_managers.add("poetry/uv/pip")
    if req_files:
        package_managers.add("pip")
    if pipfile_files:
        package_managers.add("pipenv")

    combined_py = "\n".join(py_contents)

    # Web frameworks
    if "fastapi" in combined_py:
        frameworks.append(FrameworkInfo(name="FastAPI", category="web_framework", config_file="requirements.txt"))
    if "flask" in combined_py:
        frameworks.append(FrameworkInfo(name="Flask", category="web_framework"))
    if "django" in combined_py:
        frameworks.append(FrameworkInfo(name="Django", category="web_framework"))
    if "tornado" in combined_py:
        frameworks.append(FrameworkInfo(name="Tornado", category="web_framework"))

    # ORM & DB
    if "sqlalchemy" in combined_py:
        frameworks.append(FrameworkInfo(name="SQLAlchemy", category="orm"))
    if "tortoise-orm" in combined_py:
        frameworks.append(FrameworkInfo(name="Tortoise ORM", category="orm"))
    if "alembic" in combined_py:
        frameworks.append(FrameworkInfo(name="Alembic", category="database_migrations"))

    # Testing
    if "pytest" in combined_py or (root_path / "pytest.ini").exists():
        test_frameworks.add("pytest")
    if "unittest" in combined_py:
        test_frameworks.add("unittest")

    # ML / AI
    if "langchain" in combined_py or "langgraph" in combined_py:
        frameworks.append(FrameworkInfo(name="LangChain/LangGraph", category="ai_agent"))
    if "torch" in combined_py or "pytorch" in combined_py:
        frameworks.append(FrameworkInfo(name="PyTorch", category="ml"))
    if "transformers" in combined_py:
        frameworks.append(FrameworkInfo(name="HuggingFace Transformers", category="ml"))

    # 4. Node / JS / TS Ecosystem (package.json)
    pkg_files = list(root_path.glob("**/package.json"))
    for pkg_path in pkg_files:
        if is_ignored_file(pkg_path, root_path):
            continue
        try:
            data = json.loads(pkg_path.read_text(encoding="utf-8", errors="ignore"))
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            deps_keys = {k.lower(): str(v) for k, v in deps.items()}

            if (root_path / "pnpm-lock.yaml").exists():
                package_managers.add("pnpm")
            elif (root_path / "yarn.lock").exists():
                package_managers.add("yarn")
            elif (root_path / "package-lock.json").exists() or pkg_files:
                package_managers.add("npm")

            # Frameworks
            if "express" in deps_keys:
                frameworks.append(FrameworkInfo(name="Express", category="web_framework", version=deps_keys.get("express")))
            if "@nestjs/core" in deps_keys or "nestjs" in deps_keys:
                frameworks.append(FrameworkInfo(name="NestJS", category="web_framework"))
            if "next" in deps_keys:
                frameworks.append(FrameworkInfo(name="Next.js", category="fullstack_framework", version=deps_keys.get("next")))
            if "react" in deps_keys:
                frameworks.append(FrameworkInfo(name="React", category="ui", version=deps_keys.get("react")))
            if "vue" in deps_keys:
                frameworks.append(FrameworkInfo(name="Vue.js", category="ui", version=deps_keys.get("vue")))
            if "svelte" in deps_keys or "@sveltejs/kit" in deps_keys:
                frameworks.append(FrameworkInfo(name="Svelte", category="ui"))
            if "tailwindcss" in deps_keys:
                frameworks.append(FrameworkInfo(name="TailwindCSS", category="styling"))
            if "prisma" in deps_keys or "@prisma/client" in deps_keys:
                frameworks.append(FrameworkInfo(name="Prisma", category="orm"))

            # Test runners
            if "jest" in deps_keys:
                test_frameworks.add("jest")
            if "vitest" in deps_keys:
                test_frameworks.add("vitest")
            if "mocha" in deps_keys:
                test_frameworks.add("mocha")
            if "@playwright/test" in deps_keys or "playwright" in deps_keys:
                test_frameworks.add("playwright")
            if "cypress" in deps_keys:
                test_frameworks.add("cypress")
        except Exception:
            pass

    # 5. Rust Ecosystem
    if (root_path / "Cargo.toml").exists():
        package_managers.add("cargo")
        test_frameworks.add("cargo test")

    # 6. Go Ecosystem
    if (root_path / "go.mod").exists():
        package_managers.add("go modules")
        test_frameworks.add("go test")

    return frameworks, sorted(package_managers), sorted(test_frameworks), has_docker, has_ci_cd


def generate_markdown_summary(
    repo_name: str,
    primary_language: str,
    languages: dict[str, LanguageStat],
    frameworks: list[FrameworkInfo],
    package_managers: list[str],
    test_frameworks: list[str],
    has_docker: bool,
    has_ci_cd: bool,
    file_count: int,
    total_loc: int,
) -> str:
    """Generate a structured Markdown architectural summary."""
    top_langs = sorted(languages.values(), key=lambda l: l.lines_of_code, reverse=True)[:5]
    lang_table_rows = "\n".join(
        f"| {l.name} | {l.file_count} | {l.lines_of_code:,} | {l.percentage:.1f}% |"
        for l in top_langs
    )

    fw_list = ", ".join(f"`{f.name}`" for f in frameworks) or "None detected"
    pm_list = ", ".join(f"`{p}`" for p in package_managers) or "Standard"
    tf_list = ", ".join(f"`{t}`" for t in test_frameworks) or "None detected"

    return f"""# Architecture & Repository Summary: {repo_name}

## 📊 Overview
- **Primary Language:** {primary_language}
- **Total Source Files:** {file_count:,}
- **Total Lines of Code:** {total_loc:,}
- **Docker Enabled:** {'✅ Yes' if has_docker else '❌ No'}
- **CI/CD Workflows:** {'✅ Yes' if has_ci_cd else '❌ No'}

## 💻 Language Breakdown
| Language | Files | Lines of Code | Percentage |
| :--- | :--- | :--- | :--- |
{lang_table_rows}

## 🛠️ Stack & Tooling
- **Frameworks & Libraries:** {fw_list}
- **Package Managers:** {pm_list}
- **Test Frameworks:** {tf_list}
"""


async def analyze_repository(repo_path: Path) -> RepositoryAnalysis:
    """
    Execute full repository scanning, language detection, framework detection,
    and file tree compilation.

    Args:
        repo_path: Root path of the cloned repository.

    Returns:
        RepositoryAnalysis instance.
    """
    repo_path = repo_path.resolve()
    logger.info("repository_analysis_started", path=str(repo_path))

    lang_stats: dict[str, dict[str, int]] = {}
    all_rel_paths: list[str] = []
    total_size_bytes = 0
    file_count = 0
    total_loc = 0

    max_file_size = settings.max_file_size_kb * 1024

    for root, dirs, files in os.walk(repo_path):
        current_dir = Path(root)

        # Filter ignored subdirectories in-place
        dirs[:] = [
            d for d in dirs
            if d not in IGNORED_DIRECTORIES and not (d.startswith(".") and d != ".github")
        ]

        for file_name in files:
            file_path = current_dir / file_name

            if is_ignored_file(file_path, repo_path):
                continue

            try:
                rel_path = str(file_path.relative_to(repo_path)).replace("\\", "/")
            except ValueError:
                rel_path = file_name

            all_rel_paths.append(rel_path)
            file_count += 1

            try:
                file_size = file_path.stat().st_size
                total_size_bytes += file_size
            except Exception:
                file_size = 0

            # Language and LOC
            lang = detect_file_language(file_path)
            if lang:
                loc = 0
                if file_size <= max_file_size:
                    loc = count_file_loc(file_path)
                    total_loc += loc

                if lang not in lang_stats:
                    lang_stats[lang] = {"files": 0, "loc": 0}
                lang_stats[lang]["files"] += 1
                lang_stats[lang]["loc"] += loc

    # Compute language percentages
    languages: dict[str, LanguageStat] = {}
    for lang, data in lang_stats.items():
        pct = (data["loc"] / total_loc * 100.0) if total_loc > 0 else (data["files"] / max(1, file_count) * 100.0)
        languages[lang] = LanguageStat(
            name=lang,
            file_count=data["files"],
            lines_of_code=data["loc"],
            percentage=round(pct, 2),
        )

    # Determine primary language
    primary_language = "Generic"
    if languages:
        primary_language = max(languages.values(), key=lambda l: l.lines_of_code).name

    # Detect frameworks and tools
    frameworks, pkg_mgrs, test_fws, has_docker, has_ci_cd = detect_frameworks_and_tools(repo_path)

    # Build hierarchical tree
    file_tree = build_file_tree_node(repo_path, repo_path) or FileTreeNode(
        name=repo_path.name, path="", is_dir=True, children=[]
    )

    # Generate summary
    summary_md = generate_markdown_summary(
        repo_name=repo_path.name,
        primary_language=primary_language,
        languages=languages,
        frameworks=frameworks,
        package_managers=pkg_mgrs,
        test_frameworks=test_fws,
        has_docker=has_docker,
        has_ci_cd=has_ci_cd,
        file_count=file_count,
        total_loc=total_loc,
    )

    logger.info(
        "repository_analysis_completed",
        primary_language=primary_language,
        total_files=file_count,
        total_loc=total_loc,
        frameworks_count=len(frameworks),
    )

    return RepositoryAnalysis(
        languages=languages,
        primary_language=primary_language,
        frameworks=frameworks,
        package_managers=pkg_mgrs,
        test_frameworks=test_fws,
        has_docker=has_docker,
        has_ci_cd=has_ci_cd,
        file_count=file_count,
        total_loc=total_loc,
        total_size_bytes=total_size_bytes,
        file_tree=file_tree,
        all_relative_paths=all_rel_paths,
        summary=summary_md,
    )
