"""
Unit tests for AST-aware semantic code chunker.
"""

from __future__ import annotations

from pathlib import Path
from app.rag.chunker import chunk_file_by_lines, chunk_source_file


def test_chunk_python_file_with_symbols():
    code = """
import os
import sys
from fastapi import FastAPI, Depends

app = FastAPI()

class AuthService:
    def __init__(self, secret: str):
        self.secret = secret

    def verify_token(self, token: str) -> bool:
        return token == self.secret

@app.post("/login")
async def login():
    return {"token": "secret123"}
"""
    chunks = chunk_source_file("app/auth.py", code, language="Python")

    assert len(chunks) >= 3

    # Check symbols
    symbol_names = [c.symbol_name for c in chunks]
    assert "AuthService" in symbol_names
    assert "AuthService.verify_token" in symbol_names
    assert "login" in symbol_names

    # Check content hash
    for c in chunks:
        assert c.content_hash is not None
        assert len(c.content_hash) == 64
        assert c.file_path == "app/auth.py"
        assert c.start_line > 0
        assert c.end_line >= c.start_line


def test_chunk_typescript_file_with_symbols():
    code = """
import express from 'express';

export class TokenManager {
    generate() { return "token"; }
}

export function validate(token: string) {
    return token.length > 0;
}
"""
    chunks = chunk_source_file("src/token.ts", code, language="TypeScript")

    assert len(chunks) >= 2
    symbol_names = [c.symbol_name for c in chunks]
    assert "TokenManager" in symbol_names
    assert "validate" in symbol_names


def test_chunk_file_by_lines_fallback():
    long_text = "\n".join([f"line_{i} = {i}" for i in range(1, 150)])
    chunks = chunk_file_by_lines("config.ini", long_text, language="INI", chunk_lines=50, overlap_lines=10)

    assert len(chunks) >= 3
    assert chunks[0].start_line == 1
    assert chunks[0].end_line == 50
    assert chunks[1].start_line == 41  # 50 - 10 + 1
