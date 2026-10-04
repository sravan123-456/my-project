#!/usr/bin/env python3
"""
Post-deploy smoke tests — run after every deployment.

Usage (inside Docker / project root):
  python scripts/smoke_test.py
  python scripts/smoke_test.py --url https://indukuru.online

Optional env for logged-in checks:
  SMOKE_ORG=indukuru  SMOKE_USER=test1  SMOKE_PASSWORD=yourpassword

Exit code 0 = all passed, 1 = one or more failed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

# Allow `python scripts/smoke_test.py` from project root (Docker WORKDIR=/app).
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass
class Result:
    name: str
    passed: bool
    detail: str = ""


class SmokeRunner:
    def __init__(self):
        self.results: list[Result] = []

    def record(self, name: str, passed: bool, detail: str = ""):
        self.results.append(Result(name, passed, detail))
        status = "PASS" if passed else "FAIL"
        line = f"  [{status}] {name}"
        if detail:
            line += f" — {detail}"
        print(line)

    def ok(self) -> bool:
        return all(r.passed for r in self.results)

    def summary(self):
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        print()
        print(f"Smoke tests: {passed}/{total} passed")
        if not self.ok():
            print("Failed:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}: {r.detail}")


def _http_get(url: str, timeout: int = 20):
    request = urllib.request.Request(url, headers={"User-Agent": "DanSetu-SmokeTest/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        return response.status, response.headers, body


def _http_get_follow(url: str, timeout: int = 20):
    request = urllib.request.Request(url, headers={"User-Agent": "DanSetu-SmokeTest/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, response.geturl(), response.read()


def run_http_smoke(base_url: str, runner: SmokeRunner):
    base = base_url.rstrip("/")

    def get(path: str):
        return _http_get(f"{base}{path}")

    # Health
    try:
        status, _, body = get("/health")
        data = json.loads(body.decode())
        runner.record("health endpoint", status == 200 and data.get("status") == "ok")
    except Exception as exc:
        runner.record("health endpoint", False, str(exc))

    # Public pages
    public_pages = [
        ("landing page", "/", ["DanSetu", "landing", "festival"]),
        ("login page", "/login", ["csrf_token", "committee"]),
        ("pricing page", "/pricing", ["pricing", "plan"]),
        ("help page", "/help", ["help"]),
    ]
    for name, path, markers in public_pages:
        try:
            status, _, body = get(path)
            text = body.decode(errors="replace").lower()
            found = any(marker.lower() in text for marker in markers)
            runner.record(name, status == 200 and found, f"HTTP {status}")
        except Exception as exc:
            runner.record(name, False, str(exc))

    # Static assets (regression: key JS/CSS must load)
    static_assets = [
        "js/msg91-registration.js",
        "js/join-registration.js",
        "js/app.js",
        "css/landing.css",
        "vendor/bootstrap.bundle.min.js",
    ]
    for asset in static_assets:
        try:
            status, _, _ = get(f"/static/{asset}")
            runner.record(f"static/{asset}", status == 200, f"HTTP {status}")
        except Exception as exc:
            runner.record(f"static/{asset}", False, str(exc))

    # Protected routes should not return 500 when logged out
    protected = [
        "/dashboard",
        "/donations/",
        "/expenses/",
        "/reports/",
        "/gallery/",
        "/admin/users",
        "/site-admin/",
        "/profile/",
        "/activity/",
    ]
    for path in protected:
        try:
            status, final_url, _ = _http_get_follow(f"{base}{path}")
            not_server_error = status < 500
            redirected_or_denied = status in (200, 302, 303, 307, 308, 401, 403) or "login" in final_url
            runner.record(
                f"protected {path}",
                not_server_error and redirected_or_denied,
                f"HTTP {status}",
            )
        except urllib.error.HTTPError as exc:
            runner.record(
                f"protected {path}",
                exc.code < 500,
                f"HTTP {exc.code}",
            )
        except Exception as exc:
            runner.record(f"protected {path}", False, str(exc))


def _extract_csrf(html: str) -> str:
    match = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    return match.group(1) if match else ""


def run_app_smoke(runner: SmokeRunner):
    from app import create_app, db
    from sqlalchemy import inspect

    from app.models import MarketingContact, Organization

    app = create_app()

    with app.test_client() as client:
        # Health
        response = client.get("/health")
        data = response.get_json()
        runner.record(
            "health endpoint",
            response.status_code == 200 and data.get("status") == "ok",
        )

        # Landing + login
        response = client.get("/")
        runner.record("landing page", response.status_code == 200)

        response = client.get("/login")
        html = response.data.decode()
        runner.record(
            "login page + CSRF",
            response.status_code == 200 and "csrf_token" in html,
        )

        for path in ("/pricing", "/help", "/reports/"):
            response = client.get(path)
            runner.record(
                f"GET {path}",
                response.status_code in (200, 302),
                f"HTTP {response.status_code}",
            )

        # Database / migrations
        with app.app_context():
            try:
                org_count = Organization.query.count()
                runner.record("database organizations table", org_count >= 0)
            except Exception as exc:
                runner.record("database organizations table", False, str(exc))

            try:
                has_table = inspect(db.engine).has_table("marketing_contacts")
                runner.record("marketing_contacts migration", has_table)
            except Exception as exc:
                runner.record("marketing_contacts migration", False, str(exc))

            from app.year_scope import get_current_festival_year

            org = Organization.query.first()
            year = get_current_festival_year(org) if org else get_current_festival_year(None)
            runner.record("festival year helper", isinstance(year, int) and year >= 2000)

            from app.msg91 import widget_config

            widget = widget_config()
            runner.record(
                "MSG91 widget config",
                widget is None or ("widget_id" in widget and "widget_token" in widget),
            )

        # Optional authenticated flow
        org_slug = os.getenv("SMOKE_ORG", "").strip()
        username = os.getenv("SMOKE_USER", "").strip()
        password = os.getenv("SMOKE_PASSWORD", "")

        if org_slug and username and password:
            response = client.get("/login")
            csrf = _extract_csrf(response.data.decode())
            response = client.post(
                "/login",
                data={
                    "csrf_token": csrf,
                    "committee_code": org_slug,
                    "username": username,
                    "password": password,
                    "login_submit": "Login",
                    "active_tab": "existing",
                },
                follow_redirects=False,
            )
            login_ok = response.status_code in (302, 303)
            runner.record("login with SMOKE_* credentials", login_ok, f"HTTP {response.status_code}")

            if login_ok:
                response = client.get("/dashboard", follow_redirects=True)
                runner.record(
                    "dashboard after login",
                    response.status_code == 200,
                    f"HTTP {response.status_code}",
                )

                response = client.get("/donations/", follow_redirects=True)
                runner.record(
                    "donations after login",
                    response.status_code == 200,
                    f"HTTP {response.status_code}",
                )

                response = client.get("/reports/", follow_redirects=True)
                runner.record(
                    "reports after login",
                    response.status_code == 200,
                    f"HTTP {response.status_code}",
                )

                response = client.get("/gallery/", follow_redirects=True)
                runner.record(
                    "gallery after login",
                    response.status_code == 200,
                    f"HTTP {response.status_code}",
                )
        else:
            runner.record(
                "login flow (skipped)",
                True,
                "set SMOKE_ORG, SMOKE_USER, SMOKE_PASSWORD to enable",
            )


def main():
    parser = argparse.ArgumentParser(description="DanSetu post-deploy smoke tests")
    parser.add_argument(
        "--url",
        help="Live site base URL (e.g. https://indukuru.online). If omitted, uses Flask test client.",
    )
    args = parser.parse_args()

    runner = SmokeRunner()
    print("DanSetu smoke tests")
    print("=" * 40)

    if args.url:
        print(f"Mode: HTTP ({args.url})")
        run_http_smoke(args.url, runner)
    else:
        print("Mode: Flask test client (in-app)")
        run_app_smoke(runner)

    runner.summary()
    sys.exit(0 if runner.ok() else 1)


if __name__ == "__main__":
    main()
