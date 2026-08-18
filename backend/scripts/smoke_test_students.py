"""End-to-end smoke test for student CRUD and class enrollment:

    login as super_admin -> create college -> create admin
    -> admin creates department + class -> admin creates two students
    -> get/list/search students -> patch stage applicant->enrolled (checks admitted_at)
    -> enroll student in class -> duplicate enroll blocked -> leave class
    -> re-enroll reactivates the same row -> delete a student -> cleanup

Run the API first, then:
    python -m scripts.smoke_test_students --username root --password "..." --base-url http://127.0.0.1:8000
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
    parser = argparse.ArgumentParser(description="Smoke test student CRUD and class enrollment")
    parser.add_argument("--username", required=True, help="super_admin username")
    parser.add_argument("--password", required=True, help="super_admin password")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    tag = uuid.uuid4().hex[:8]
    college_code = f"STU{tag[:6]}".upper()
    admin_username = f"stu_admin_{tag}"
    password = "SmokeTest123!"

    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        super_token = login(client, args.username, args.password)
        sh = auth_headers(super_token)

        r = client.post("/admin/colleges", headers=sh, json={
            "name": f"Student Smoke College {tag}", "code": college_code,
        })
        check(r.status_code == 201, f"create college -> 201 (got {r.status_code}: {r.text})")
        college_id = r.json()["id"]

        r = client.post("/admin/users", headers=sh, json={
            "username": admin_username, "password": password, "role": "admin",
            "college_id": college_id, "profile": {"name": "Student Smoke Admin"},
        })
        check(r.status_code == 201, f"create admin -> 201 (got {r.status_code}: {r.text})")
        admin_id = r.json()["id"]
        admin_token = login(client, admin_username, password)
        ah = auth_headers(admin_token)

        r = client.post("/admin/departments", headers=ah, json={"name": f"Dept-{tag}"})
        check(r.status_code == 201, f"create department -> 201 (got {r.status_code}: {r.text})")
        department_id = r.json()["id"]

        r = client.post("/admin/classes", headers=ah, json={"department_id": department_id, "name": "A"})
        check(r.status_code == 201, f"create class -> 201 (got {r.status_code}: {r.text})")
        class_id = r.json()["id"]

        # --- create students ---
        r = client.post("/admin/students", headers=ah, json={
            "register_number": f"REG-{tag}-1",
            "application_number": f"APP-{tag}-1",
            "profile": {"name": "Alice Applicant"},
        })
        check(r.status_code == 201, f"create student 1 -> 201 (got {r.status_code}: {r.text})")
        student1 = r.json()
        check(student1["stage"] == "applicant" and student1["has_login"] is False, "student 1 defaults: applicant, no login")
        student1_id = student1["id"]

        r = client.post("/admin/students", headers=ah, json={
            "register_number": f"REG-{tag}-2",
            "profile": {"name": "Bob Applicant"},
        })
        check(r.status_code == 201, f"create student 2 -> 201 (got {r.status_code}: {r.text})")
        student2_id = r.json()["id"]

        # duplicate register_number rejected
        r = client.post("/admin/students", headers=ah, json={
            "register_number": f"REG-{tag}-1",
            "profile": {"name": "Duplicate"},
        })
        check(r.status_code == 409, f"duplicate register_number -> 409 (got {r.status_code})")

        # --- list / get / search ---
        r = client.get("/admin/students", headers=ah)
        check(r.status_code == 200 and len(r.json()) == 2, "list students -> 2")

        r = client.get("/admin/students", headers=ah, params={"q": "Alice"})
        check(r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["id"] == student1_id, "search by name prefix finds student 1")

        r = client.get(f"/admin/students/{student1_id}", headers=ah)
        check(r.status_code == 200, "get student 1 -> 200")

        # --- patch stage applicant -> enrolled sets admitted_at ---
        r = client.patch(f"/admin/students/{student1_id}", headers=ah, json={"stage": "enrolled", "tenth_mark": "91.50"})
        check(r.status_code == 200, f"patch student stage -> 200 (got {r.status_code}: {r.text})")
        updated = r.json()
        check(updated["stage"] == "enrolled" and updated["admitted_at"] is not None, "stage=enrolled auto-sets admitted_at")
        check(str(updated["tenth_mark"]) == "91.5" or float(updated["tenth_mark"]) == 91.5, "tenth_mark saved")

        r = client.get("/admin/students", headers=ah, params={"stage": "enrolled"})
        check(r.status_code == 200 and len(r.json()) == 1, "filter students by stage=enrolled")

        # --- class enrollment ---
        r = client.post(f"/admin/students/{student1_id}/classes", headers=ah, json={"class_id": class_id, "academic_year": "2026"})
        check(r.status_code == 201, f"enroll student in class -> 201 (got {r.status_code}: {r.text})")

        r = client.post(f"/admin/students/{student1_id}/classes", headers=ah, json={"class_id": class_id})
        check(r.status_code == 409, f"duplicate enrollment -> 409 (got {r.status_code})")

        r = client.get(f"/admin/students/{student1_id}/classes", headers=ah)
        check(r.status_code == 200 and len(r.json()) == 1, "list active class enrollments -> 1")

        r = client.delete(f"/admin/students/{student1_id}/classes/{class_id}", headers=ah)
        check(r.status_code == 204, "leave class -> 204")

        r = client.get(f"/admin/students/{student1_id}/classes", headers=ah)
        check(r.status_code == 200 and len(r.json()) == 0, "active enrollments empty after leaving")

        r = client.get(f"/admin/students/{student1_id}/classes", headers=ah, params={"include_left": True})
        check(r.status_code == 200 and len(r.json()) == 1 and r.json()[0]["left_at"] is not None, "include_left shows the left enrollment")

        r = client.post(f"/admin/students/{student1_id}/classes", headers=ah, json={"class_id": class_id})
        check(r.status_code == 201, f"re-enroll reactivates -> 201 (got {r.status_code}: {r.text})")

        # --- delete ---
        r = client.delete(f"/admin/students/{student2_id}", headers=ah)
        check(r.status_code == 204, "delete student 2 (no history) -> 204")

        r = client.get(f"/admin/students/{student2_id}", headers=ah)
        check(r.status_code == 404, "deleted student no longer found")

        # --- cleanup ---
        r = client.delete(f"/admin/students/{student1_id}/classes/{class_id}", headers=ah)
        check(r.status_code == 204, "cleanup: leave class -> 204")

        r = client.delete(f"/admin/students/{student1_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete student 1 -> 204")

        r = client.delete(f"/admin/classes/{class_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete class -> 204")

        r = client.delete(f"/admin/departments/{department_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete department -> 204")

        r = client.delete(f"/admin/users/{admin_id}", headers=sh)
        check(r.status_code == 204, "cleanup: deactivate admin -> 204")

        r = client.delete(f"/admin/colleges/{college_id}", headers=sh)
        check(r.status_code == 204, "cleanup: deactivate college -> 204")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
