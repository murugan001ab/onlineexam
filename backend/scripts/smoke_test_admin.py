"""End-to-end smoke test for the admin/user CRUD chain:

    login as super_admin -> create college -> create admin for that college
    -> login as that admin -> create staff -> list/get/patch/deactivate staff
    -> super_admin deactivates college

Run the API first (uvicorn main:app --reload), make sure roles are seeded
and a super_admin exists (see scripts/create_super_admin.py), then:

    python -m scripts.smoke_test_admin --username root --password "..." --base-url http://127.0.0.1:8000

Exits non-zero on the first failed assertion, printing what failed.
"""
import argparse
import sys
import uuid

import httpx


def check(condition: bool, message: str) -> None:
    if not condition:
        print(f"FAILED: {message}", file=sys.stderr)
        sys.exit(1)
    print(f"ok - {message}")


def login(client: httpx.Client, username: str, password: str) -> str:
    r = client.post("/auth/login", json={"username": username, "password": password})
    check(r.status_code == 200, f"login as '{username}' -> 200 (got {r.status_code}: {r.text})")
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test admin/user CRUD")
    parser.add_argument("--username", required=True, help="super_admin username")
    parser.add_argument("--password", required=True, help="super_admin password")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    tag = uuid.uuid4().hex[:8]
    college_code = f"SMK{tag[:6]}".upper()
    admin_username = f"smk_admin_{tag}"
    staff_username = f"smk_staff_{tag}"
    password = "SmokeTest123!"

    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        super_token = login(client, args.username, args.password)
        sh = auth_headers(super_token)

        # --- college CRUD ---
        r = client.post("/admin/colleges", headers=sh, json={
            "name": f"Smoke Test College {tag}",
            "code": college_code,
        })
        check(r.status_code == 201, f"create college -> 201 (got {r.status_code}: {r.text})")
        college = r.json()
        college_id = college["id"]

        r = client.get(f"/admin/colleges/{college_id}", headers=sh)
        check(r.status_code == 200, "get college -> 200")

        r = client.patch(f"/admin/colleges/{college_id}", headers=sh, json={"city": "Testville"})
        check(r.status_code == 200 and r.json()["city"] == "Testville", "patch college city")

        # --- super_admin creates an admin for that college ---
        r = client.post("/admin/users", headers=sh, json={
            "username": admin_username,
            "password": password,
            "role": "admin",
            "college_id": college_id,
            "profile": {"name": "Smoke Admin"},
        })
        check(r.status_code == 201, f"super_admin create admin -> 201 (got {r.status_code}: {r.text})")
        admin_user = r.json()
        check(admin_user["role"] == "admin" and admin_user["college_id"] == college_id, "created admin has correct role/college")

        # super_admin should NOT be able to create a second super_admin via this route (schema forbids it)
        r = client.post("/admin/users", headers=sh, json={
            "username": f"smk_bad_{tag}",
            "password": password,
            "role": "super_admin",
            "profile": {"name": "Should Fail"},
        })
        check(r.status_code == 422, f"creating role=super_admin via API is rejected -> 422 (got {r.status_code})")

        # --- log in as the new admin ---
        admin_token = login(client, admin_username, password)
        ah = auth_headers(admin_token)

        # admin cannot create another admin
        r = client.post("/admin/users", headers=ah, json={
            "username": f"smk_admin2_{tag}",
            "password": password,
            "role": "admin",
            "college_id": college_id,
            "profile": {"name": "Should Fail"},
        })
        check(r.status_code == 403, f"admin cannot create admin -> 403 (got {r.status_code})")

        # admin creates staff in their own college
        r = client.post("/admin/users", headers=ah, json={
            "username": staff_username,
            "password": password,
            "role": "staff",
            "profile": {"name": "Smoke Staff"},
        })
        check(r.status_code == 201, f"admin create staff -> 201 (got {r.status_code}: {r.text})")
        staff_user = r.json()
        check(staff_user["college_id"] == college_id, "staff auto-assigned to admin's college")
        staff_id = staff_user["id"]

        # admin lists users -> should only see staff, not themself/other admins
        r = client.get("/admin/users", headers=ah)
        check(r.status_code == 200, "admin list users -> 200")
        roles_seen = {u["role"] for u in r.json()}
        check(roles_seen <= {"staff"}, f"admin's user list only contains staff (saw {roles_seen})")

        # admin cannot reassign staff to another college
        r = client.patch(f"/admin/users/{staff_id}", headers=ah, json={"college_id": college_id + 1})
        check(r.status_code in (403, 400), f"admin cannot reassign college -> 403/400 (got {r.status_code})")

        # admin patches staff profile
        r = client.patch(f"/admin/users/{staff_id}", headers=ah, json={"profile": {"phone": "9999999999"}})
        check(r.status_code == 200 and r.json()["profile"]["phone"] == "9999999999", "admin patches staff profile")

        # login as staff works
        staff_token = login(client, staff_username, password)

        # /auth/me reflects the logged-in user
        r = client.get("/auth/me", headers=auth_headers(staff_token))
        check(r.status_code == 200 and r.json()["username"] == staff_username, "staff /auth/me -> self")

        # staff can self-service change their own password
        new_staff_password = "SmokeTestChanged123!"
        r = client.post("/auth/change-password", headers=auth_headers(staff_token), json={
            "current_password": password,
            "new_password": new_staff_password,
        })
        check(r.status_code == 204, f"staff change-password -> 204 (got {r.status_code}: {r.text})")

        r = client.post("/auth/login", json={"username": staff_username, "password": password})
        check(r.status_code == 401, "old password rejected after change")

        login(client, staff_username, new_staff_password)

        r = client.post("/auth/change-password", headers=auth_headers(staff_token), json={
            "current_password": "totally-wrong",
            "new_password": "WhateverElse123!",
        })
        check(r.status_code == 401, f"change-password rejects wrong current password -> 401 (got {r.status_code})")

        # admin deactivates staff
        r = client.delete(f"/admin/users/{staff_id}", headers=ah)
        check(r.status_code == 204, f"admin deactivate staff -> 204 (got {r.status_code})")

        # deactivated staff can no longer log in
        r = client.post("/auth/login", json={"username": staff_username, "password": password})
        check(r.status_code == 401, f"deactivated staff login -> 401 (got {r.status_code})")

        # --- cleanup: super_admin deactivates the admin and the college ---
        r = client.delete(f"/admin/users/{admin_user['id']}", headers=sh)
        check(r.status_code == 204, "super_admin deactivate admin -> 204")

        r = client.delete(f"/admin/colleges/{college_id}", headers=sh)
        check(r.status_code == 204, "super_admin deactivate college -> 204")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
