"""End-to-end smoke test for department/class CRUD and staff assignment:

    login as super_admin -> create college -> create admin -> create staff
    -> admin creates department -> admin creates class in it
    -> admin assigns staff to department -> admin assigns staff to class (incharge)
    -> toggle incharge -> unassign both -> delete class -> delete department
    -> verify department delete is blocked while a class still exists

Run the API first, then:
    python -m scripts.smoke_test_organization --username root --password "..." --base-url http://127.0.0.1:8000
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
    parser = argparse.ArgumentParser(description="Smoke test department/class/staff-assignment CRUD")
    parser.add_argument("--username", required=True, help="super_admin username")
    parser.add_argument("--password", required=True, help="super_admin password")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    tag = uuid.uuid4().hex[:8]
    college_code = f"ORG{tag[:6]}".upper()
    admin_username = f"org_admin_{tag}"
    staff_username = f"org_staff_{tag}"
    password = "SmokeTest123!"

    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        super_token = login(client, args.username, args.password)
        sh = auth_headers(super_token)

        r = client.post("/admin/colleges", headers=sh, json={
            "name": f"Org Smoke College {tag}", "code": college_code,
        })
        check(r.status_code == 201, f"create college -> 201 (got {r.status_code}: {r.text})")
        college_id = r.json()["id"]

        r = client.post("/admin/users", headers=sh, json={
            "username": admin_username, "password": password, "role": "admin",
            "college_id": college_id, "profile": {"name": "Org Admin"},
        })
        check(r.status_code == 201, f"create admin -> 201 (got {r.status_code}: {r.text})")
        admin_id = r.json()["id"]
        admin_token = login(client, admin_username, password)
        ah = auth_headers(admin_token)

        r = client.post("/admin/users", headers=ah, json={
            "username": staff_username, "password": password, "role": "staff",
            "profile": {"name": "Org Staff"},
        })
        check(r.status_code == 201, f"admin create staff -> 201 (got {r.status_code}: {r.text})")
        staff_id = r.json()["id"]

        # --- departments ---
        r = client.post("/admin/departments", headers=ah, json={"name": f"CSE-{tag}", "code": "CSE"})
        check(r.status_code == 201, f"admin create department -> 201 (got {r.status_code}: {r.text})")
        department = r.json()
        check(department["college_id"] == college_id, "department auto-scoped to admin's college")
        department_id = department["id"]

        # admin can't create a department in another college (super_admin's college_id ignored, forced to own)
        r = client.post("/admin/departments", headers=ah, json={"name": "Sneaky", "college_id": college_id + 1})
        check(r.json()["college_id"] == college_id, "admin's college_id override is ignored, forced to own college")

        r = client.get(f"/admin/departments/{department_id}", headers=ah)
        check(r.status_code == 200, "get department -> 200")

        r = client.patch(f"/admin/departments/{department_id}", headers=ah, json={"code": "CS"})
        check(r.status_code == 200 and r.json()["code"] == "CS", "patch department code")

        # --- classes ---
        r = client.post("/admin/classes", headers=ah, json={
            "department_id": department_id, "name": "CSE-A", "section": "A", "academic_year": "2026",
        })
        check(r.status_code == 201, f"admin create class -> 201 (got {r.status_code}: {r.text})")
        class_id = r.json()["id"]
        check(r.json()["college_id"] == college_id, "class inherits department's college_id")

        r = client.get("/admin/classes", headers=ah, params={"department_id": department_id})
        check(r.status_code == 200 and len(r.json()) == 1, "list classes filtered by department")

        # --- department delete blocked while class exists ---
        r = client.delete(f"/admin/departments/{department_id}", headers=ah)
        check(r.status_code == 409, f"delete department with class still attached -> 409 (got {r.status_code})")

        # --- staff department assignment ---
        r = client.post(f"/admin/staff/{staff_id}/departments", headers=ah, json={"department_id": department_id})
        check(r.status_code == 201, f"assign staff to department -> 201 (got {r.status_code}: {r.text})")

        r = client.post(f"/admin/staff/{staff_id}/departments", headers=ah, json={"department_id": department_id})
        check(r.status_code == 409, f"duplicate department assignment -> 409 (got {r.status_code})")

        r = client.get(f"/admin/staff/{staff_id}/departments", headers=ah)
        check(r.status_code == 200 and len(r.json()) == 1, "list staff departments")

        r = client.delete(f"/admin/staff/{staff_id}/departments/{department_id}", headers=ah)
        check(r.status_code == 204, "unassign staff department -> 204")

        r = client.get(f"/admin/staff/{staff_id}/departments", headers=ah)
        check(r.status_code == 200 and len(r.json()) == 0, "unassigned department no longer listed (default active-only)")

        # reassign should work again (reactivates the soft-deleted row)
        r = client.post(f"/admin/staff/{staff_id}/departments", headers=ah, json={"department_id": department_id})
        check(r.status_code == 201, f"reassign staff to department after unassign -> 201 (got {r.status_code}: {r.text})")

        # --- staff class assignment ---
        r = client.post(f"/admin/staff/{staff_id}/classes", headers=ah, json={"class_id": class_id, "is_incharge": False})
        check(r.status_code == 201, f"assign staff to class -> 201 (got {r.status_code}: {r.text})")

        r = client.post(f"/admin/staff/{staff_id}/classes", headers=ah, json={"class_id": class_id})
        check(r.status_code == 409, f"duplicate class assignment -> 409 (got {r.status_code})")

        r = client.patch(f"/admin/staff/{staff_id}/classes/{class_id}", headers=ah, json={"is_incharge": True})
        check(r.status_code == 200 and r.json()["is_incharge"] is True, "toggle is_incharge -> True")

        r = client.get(f"/admin/staff/{staff_id}/classes", headers=ah)
        check(r.status_code == 200 and len(r.json()) == 1, "list staff classes")

        r = client.delete(f"/admin/staff/{staff_id}/classes/{class_id}", headers=ah)
        check(r.status_code == 204, "unassign staff class -> 204")

        # --- cleanup ---
        r = client.delete(f"/admin/staff/{staff_id}/departments/{department_id}", headers=ah)
        check(r.status_code == 204, "cleanup: unassign staff department -> 204")

        r = client.delete(f"/admin/classes/{class_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete class -> 204")

        r = client.delete(f"/admin/departments/{department_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete department (now empty) -> 204")

        r = client.delete(f"/admin/users/{staff_id}", headers=ah)
        check(r.status_code == 204, "cleanup: deactivate staff -> 204")

        r = client.delete(f"/admin/users/{admin_id}", headers=sh)
        check(r.status_code == 204, "cleanup: deactivate admin -> 204")

        r = client.delete(f"/admin/colleges/{college_id}", headers=sh)
        check(r.status_code == 204, "cleanup: deactivate college -> 204")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
