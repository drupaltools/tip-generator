"""Tests for Flask web viewer routes."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tip_generator import viewer


@pytest.fixture
def app_client(sample_tip_dir):
    """Create a Flask test client with a sample tips directory."""
    with patch("tip_generator.viewer.TIPS_DIR", sample_tip_dir):
        with viewer.app.test_client() as client:
            yield client


class TestHomeRoute:
    def test_index_returns_200(self, app_client):
        response = app_client.get("/")
        assert response.status_code == 200
        assert b"category" in response.data.lower() or b"tip" in response.data.lower()

    def test_about_returns_200(self, app_client):
        response = app_client.get("/about")
        assert response.status_code == 200


class TestApiRoutes:
    def test_api_categories(self, app_client):
        response = app_client.get("/api/categories")
        assert response.status_code == 200
        data = response.get_json()
        assert "categories" in data
        assert len(data["categories"]) == 2

    def test_api_tips(self, app_client):
        response = app_client.get("/api/tips")
        assert response.status_code == 200
        data = response.get_json()
        assert "tips" in data
        assert data["count"] == 3

    def test_api_tips_filter_by_category(self, app_client):
        response = app_client.get("/api/tips?category=core-service")
        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2
        for tip in data["tips"]:
            assert tip["category"] == "core-service"

    def test_api_random(self, app_client):
        response = app_client.get("/api/random")
        assert response.status_code == 200
        data = response.get_json()
        assert "content" in data or "uuid" in data

    def test_api_random_with_category(self, app_client):
        response = app_client.get("/api/random?category=rare-drush-command")
        assert response.status_code == 200
        data = response.get_json()
        assert data["category"] == "rare-drush-command"


class TestEmptyTips:
    def test_api_random_404_for_empty(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with patch("tip_generator.viewer.TIPS_DIR", empty_dir):
            with viewer.app.test_client() as client:
                response = client.get("/api/random")
                assert response.status_code == 404
