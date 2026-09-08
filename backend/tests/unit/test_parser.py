"""
Unit tests for AST and JS/TS symbol parsers.
"""

from __future__ import annotations

from pathlib import Path
from app.repository.parser import parse_source_file


def test_python_ast_parser():
    code = """
import os
from fastapi import FastAPI, Depends

app = FastAPI()

class User(BaseModel):
    name: str

    def get_name(self) -> str:
        return self.name

@app.get("/users")
async def list_users():
    return []
"""
    symbols, imports = parse_source_file(Path("test.py"), code, language="Python")

    assert "os" in imports
    assert "fastapi.FastAPI" in imports

    symbol_names = [s.name for s in symbols]
    assert "User" in symbol_names
    assert "User.get_name" in symbol_names
    assert "list_users" in symbol_names

    route = next(s for s in symbols if s.name == "list_users")
    assert route.symbol_type == "route"


def test_typescript_parser():
    code = """
import React, { useState } from 'react';
import express from 'express';

const app = express();

export class UserService {
    getUser() {}
}

export function calculateTotal(a: number, b: number): number {
    return a + b;
}

app.get('/api/health', (req, res) => {
    res.json({ ok: true });
});
"""
    symbols, imports = parse_source_file(Path("service.ts"), code, language="TypeScript")

    assert "react" in imports
    assert "express" in imports

    symbol_names = [s.name for s in symbols]
    assert "UserService" in symbol_names
    assert "calculateTotal" in symbol_names
    assert "GET /api/health" in symbol_names
