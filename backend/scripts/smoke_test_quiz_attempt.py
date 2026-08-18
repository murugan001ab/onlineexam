"""End-to-end smoke test for the class-quiz attempt flow:

    login as super_admin -> create college -> create admin
    -> admin: department, class, topic, 2 questions, quiz (type=class, published),
       assign quiz to class, create a student, enroll student in class,
       provision a login for that student directly (bypassing the exam-invite
       flow, since this is the class-test path)
    -> student: list available quizzes -> start attempt -> get questions
       -> answer both -> submit -> score matches expected
    -> admin: list attempts for the quiz, review answers
    -> edge cases: quiz not assigned to class is invisible/blocked;
       answering after submit is rejected

Run the API first, then:
    python -m scripts.smoke_test_quiz_attempt --username root --password "..." --base-url http://127.0.0.1:8000
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
    parser = argparse.ArgumentParser(description="Smoke test class-quiz attempt flow")
    parser.add_argument("--username", required=True, help="super_admin username")
    parser.add_argument("--password", required=True, help="super_admin password")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    tag = uuid.uuid4().hex[:8]
    college_code = f"QZ{tag[:6]}".upper()
    admin_username = f"qz_admin_{tag}"
    password = "SmokeTest123!"

    with httpx.Client(base_url=args.base_url, timeout=10) as client:
        super_token = login(client, args.username, args.password)
        sh = auth_headers(super_token)

        r = client.post("/admin/colleges", headers=sh, json={"name": f"Quiz Smoke College {tag}", "code": college_code})
        check(r.status_code == 201, f"create college -> 201 (got {r.status_code}: {r.text})")
        college_id = r.json()["id"]

        r = client.post("/admin/users", headers=sh, json={
            "username": admin_username, "password": password, "role": "admin",
            "college_id": college_id, "profile": {"name": "Quiz Smoke Admin"},
        })
        check(r.status_code == 201, f"create admin -> 201 (got {r.status_code}: {r.text})")
        admin_id = r.json()["id"]
        admin_token = login(client, admin_username, password)
        ah = auth_headers(admin_token)

        r = client.post("/admin/departments", headers=ah, json={"name": f"Dept-{tag}"})
        check(r.status_code == 201, "create department -> 201")
        department_id = r.json()["id"]

        r = client.post("/admin/classes", headers=ah, json={"department_id": department_id, "name": "A"})
        check(r.status_code == 201, "create class -> 201")
        class_id = r.json()["id"]

        r = client.post("/admin/classes", headers=ah, json={"department_id": department_id, "name": "B"})
        check(r.status_code == 201, "create second class (not targeted) -> 201")
        other_class_id = r.json()["id"]

        r = client.post("/topics", headers=ah, json={"name": f"Topic-{tag}", "slug": f"topic-{tag}"})
        check(r.status_code == 201, f"create topic -> 201 (got {r.status_code}: {r.text})")
        topic_id = r.json()["id"]

        q_ids = []
        for i, (text, correct) in enumerate([("2 + 2 = ?", "4"), ("Capital of France?", "Paris")]):
            r = client.post("/admin/questions", headers=ah, json={
                "topic_id": topic_id, "text": text, "question_type": "single_choice",
                "options": ["1", "4", "Paris", "London"], "correct_answer": correct, "marks": 5,
            })
            check(r.status_code == 201, f"create question {i} -> 201 (got {r.status_code}: {r.text})")
            q_ids.append(r.json()["id"])

        r = client.post("/admin/quizzes", headers=ah, json={
            "name": f"Quiz-{tag}", "quiz_type": "class", "status": "published", "duration_minutes": 30,
        })
        check(r.status_code == 201, f"create quiz -> 201 (got {r.status_code}: {r.text})")
        quiz_id = r.json()["id"]

        for qid in q_ids:
            r = client.post(f"/admin/quizzes/{quiz_id}/questions", headers=ah, json={"question_id": qid})
            check(r.status_code == 201, f"add question {qid} to quiz -> 201 (got {r.status_code}: {r.text})")

        r = client.post(f"/admin/quizzes/{quiz_id}/class-targets", headers=ah, json={"class_id": class_id})
        check(r.status_code == 201, f"assign quiz to class -> 201 (got {r.status_code}: {r.text})")

        r = client.post("/admin/students", headers=ah, json={"profile": {"name": "Quiz Student"}})
        check(r.status_code == 201, "create student -> 201")
        student_id = r.json()["id"]

        r = client.post(f"/admin/students/{student_id}/classes", headers=ah, json={"class_id": class_id})
        check(r.status_code == 201, "enroll student in class -> 201")

        print(
            "\nNOTE: there is currently no API endpoint to provision a login for a "
            "student outside the exam-registration invitation flow "
            "(POST /admin/exams/{exam_id}/invitations/generate). A student added "
            "here purely for a class quiz has no way to get credentials yet \u2014 see "
            "the chat writeup for a proposed fix. Skipping the student-facing half "
            "of this smoke test as a result.\n"
        )

        # --- admin-side checks that don't need a student login ---
        r = client.get(f"/admin/quizzes/{quiz_id}/attempts", headers=ah)
        check(r.status_code == 200 and len(r.json()) == 0, "list quiz attempts (none yet) -> 200, empty")

        # --- cleanup ---
        r = client.delete(f"/admin/students/{student_id}/classes/{class_id}", headers=ah)
        check(r.status_code == 204, "cleanup: leave class -> 204")
        r = client.delete(f"/admin/students/{student_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete student -> 204")
        r = client.delete(f"/admin/quizzes/{quiz_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete quiz -> 204")
        r = client.delete(f"/topics/{topic_id}", headers=ah)
        check(r.status_code in (204, 409), f"cleanup: delete topic -> 204 or 409 if referenced (got {r.status_code})")
        r = client.delete(f"/admin/classes/{class_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete class A -> 204")
        r = client.delete(f"/admin/classes/{other_class_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete class B -> 204")
        r = client.delete(f"/admin/departments/{department_id}", headers=ah)
        check(r.status_code == 204, "cleanup: delete department -> 204")
        r = client.delete(f"/admin/users/{admin_id}", headers=sh)
        check(r.status_code == 204, "cleanup: deactivate admin -> 204")
        r = client.delete(f"/admin/colleges/{college_id}", headers=sh)
        check(r.status_code == 204, "cleanup: deactivate college -> 204")

    print("\nPartial checks passed (student-facing flow needs a real student login — see note above).")


if __name__ == "__main__":
    main()
