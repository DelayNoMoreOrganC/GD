# -*- coding: utf-8 -*-
"""Phase-1 API tests: auth, case CRUD, org isolation (no OCR/Word)."""
from __future__ import annotations

import os
import sys

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import engine, AsyncSessionLocal
from app.models import Base


@pytest.fixture(scope="function")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _login(ac, username="admin", password="admin123"):
    r = await ac.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_login_and_me(client):
    token = await _login(client)
    r = await client.get("/api/auth/me", headers={"Authorization": "Bearer " + token})
    assert r.status_code == 200
    assert r.json()["username"] == "admin"
    assert r.json()["role"] == "admin"


@pytest.mark.asyncio
async def test_bad_password(client):
    r = await client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_case_crud(client):
    token = await _login(client)
    h = {"Authorization": "Bearer " + token}
    r = await client.post("/api/cases", json={"title": "T-case", "case_type": "civil"}, headers=h)
    assert r.status_code == 201
    cid = r.json()["id"]
    r2 = await client.get("/api/cases", headers=h)
    assert r2.status_code == 200
    assert any(c["id"] == cid for c in r2.json())
    r3 = await client.get("/api/cases/" + cid, headers=h)
    assert r3.status_code == 200
    assert r3.json()["title"] == "T-case"
    r4 = await client.delete("/api/cases/" + cid, headers=h)
    assert r4.status_code == 204


@pytest.mark.asyncio
async def test_protected_without_token(client):
    r = await client.get("/api/cases")
    assert r.status_code == 401
