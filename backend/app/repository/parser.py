"""
AST-based symbol and code intelligence parser.

Extracts classes, functions, methods, imports, routes, and data models
from source files without relying solely on LLMs.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Optional


class CodeSymbol:
    """Represents a code symbol (class, function, method, endpoint, model)."""

    def __init__(
        self,
        name: str,
        symbol_type: str,  # class | function | method | route | model
        start_line: int,
        end_line: int,
        docstring: Optional[str] = None,
        parameters: Optional[list[str]] = None,
        decorators: Optional[list[str]] = None,
        parent: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.symbol_type = symbol_type
        self.start_line = start_line
        self.end_line = end_line
        self.docstring = docstring
        self.parameters = parameters or []
        self.decorators = decorators or []
        self.parent = parent
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "symbol_type": self.symbol_type,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "parameters": self.parameters,
            "decorators": self.decorators,
            "parent": self.parent,
            "metadata": self.metadata,
        }


class PythonASTParser:
    """AST parser for Python files using Python's native `ast` module."""

    @staticmethod
    def parse(content: str) -> tuple[list[CodeSymbol], list[str]]:
        """
        Parse Python source code and extract symbols and imports.

        Returns:
            (symbols, imports) tuple.
        """
        symbols: list[CodeSymbol] = []
        imports: list[str] = []

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return [], []

        for node in ast.iter_child_nodes(tree):
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

            # Classes
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                decorators = [ast.unparse(d) for d in node.decorator_list]
                bases = [ast.unparse(b) for b in node.bases]
                is_model = any("base" in b.lower() or "model" in b.lower() for b in bases)

                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type="model" if is_model else "class",
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        docstring=doc,
                        decorators=decorators,
                        metadata={"bases": bases},
                    )
                )

                # Class methods
                for class_node in node.body:
                    if isinstance(class_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        method_doc = ast.get_docstring(class_node)
                        method_decorators = [ast.unparse(d) for d in class_node.decorator_list]
                        params = [arg.arg for arg in class_node.args.args]

                        symbols.append(
                            CodeSymbol(
                                name=f"{node.name}.{class_node.name}",
                                symbol_type="method",
                                start_line=class_node.lineno,
                                end_line=class_node.end_lineno or class_node.lineno,
                                docstring=method_doc,
                                parameters=params,
                                decorators=method_decorators,
                                parent=node.name,
                            )
                        )

            # Top-level Functions & Route handlers
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                decorators = [ast.unparse(d) for d in node.decorator_list]
                params = [arg.arg for arg in node.args.args]

                is_route = any(
                    any(verb in d.lower() for verb in ("get(", "post(", "put(", "delete(", "patch(", "route("))
                    for d in decorators
                )

                symbols.append(
                    CodeSymbol(
                        name=node.name,
                        symbol_type="route" if is_route else "function",
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        docstring=doc,
                        parameters=params,
                        decorators=decorators,
                    )
                )

        return symbols, imports


class JavaScriptTypeScriptParser:
    """Symbol extractor for JavaScript and TypeScript source files."""

    # Regex patterns for functions, classes, routes, and imports
    CLASS_PATTERN = re.compile(r"class\s+([A-Za-z0-9_$]+)(?:\s+extends\s+([A-Za-z0-9_$]+))?", re.MULTILINE)
    FUNC_PATTERN = re.compile(r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(([^)]*)\)", re.MULTILINE)
    CONST_FUNC_PATTERN = re.compile(
        r"(?:export\s+)?const\s+([A-Za-z0-9_$]+)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*(?::\s*[^=]+)?\s*=>",
        re.MULTILINE,
    )
    ROUTE_PATTERN = re.compile(
        r"(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )
    IMPORT_PATTERN = re.compile(
        r"(?:import\s+(?:.+?\s+from\s+)?|require\(\s*)['\"]([^'\"]+)['\"]",
        re.MULTILINE,
    )

    @classmethod
    def parse(cls, content: str) -> tuple[list[CodeSymbol], list[str]]:
        symbols: list[CodeSymbol] = []
        imports: list[str] = []

        lines = content.splitlines()

        # Imports
        for match in cls.IMPORT_PATTERN.finditer(content):
            imports.append(match.group(1))

        # Classes
        for match in cls.CLASS_PATTERN.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            symbols.append(
                CodeSymbol(
                    name=match.group(1),
                    symbol_type="class",
                    start_line=line_no,
                    end_line=line_no,
                    metadata={"extends": match.group(2) if match.group(2) else None},
                )
            )

        # Functions
        for match in cls.FUNC_PATTERN.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            params = [p.strip().split(":")[0].strip() for p in match.group(2).split(",") if p.strip()]
            symbols.append(
                CodeSymbol(
                    name=match.group(1),
                    symbol_type="function",
                    start_line=line_no,
                    end_line=line_no,
                    parameters=params,
                )
            )

        # Arrow Functions / Functional Components
        for match in cls.CONST_FUNC_PATTERN.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            params = [p.strip().split(":")[0].strip() for p in match.group(2).split(",") if p.strip()]
            symbols.append(
                CodeSymbol(
                    name=match.group(1),
                    symbol_type="function",
                    start_line=line_no,
                    end_line=line_no,
                    parameters=params,
                )
            )

        # Express / Fastify Routes
        for match in cls.ROUTE_PATTERN.finditer(content):
            line_no = content[:match.start()].count("\n") + 1
            method = match.group(1).upper()
            path = match.group(2)
            symbols.append(
                CodeSymbol(
                    name=f"{method} {path}",
                    symbol_type="route",
                    start_line=line_no,
                    end_line=line_no,
                    metadata={"method": method, "path": path},
                )
            )

        return symbols, imports


def parse_source_file(file_path: Path, content: str, language: Optional[str] = None) -> tuple[list[CodeSymbol], list[str]]:
    """
    Parse a source file based on language and extract symbols and imports.

    Args:
        file_path: Path to the source file.
        content: Raw source code string.
        language: Optional language name (inferred from suffix if omitted).

    Returns:
        (symbols, imports) tuple.
    """
    if language == "Python" or file_path.suffix.lower() == ".py":
        return PythonASTParser.parse(content)
    elif language in ("JavaScript", "TypeScript") or file_path.suffix.lower() in (".js", ".jsx", ".ts", ".tsx"):
        return JavaScriptTypeScriptParser.parse(content)
    return [], []
