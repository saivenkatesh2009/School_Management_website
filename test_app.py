import os
import sqlite3
import tempfile
import unittest

import app as school_app


class SchoolPortalTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        school_app.app.config.update(
            TESTING=True,
            SECRET_KEY="test-secret",
            DATABASE=os.path.join(self.temp_dir.name, "test-school.db"),
        )
        school_app.init_db()
        self.client = school_app.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def sign_in(self, username, password):
        return self.client.post(
            "/login",
            data={"username": username, "password": password},
            follow_redirects=True,
        )

    def test_public_home_and_student_registration(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"A place to grow.", response.data)
        self.assertIn(b"GREEN SCHOOLS", response.data)
        self.assertIn(b"green-schools-campus.jpg", response.data)
        self.assertIn(b"Welcome to GREEN SCHOOLS", response.data)
        self.assertNotIn(b"ZPH High School", response.data)
        for section in (b"about", b"academics", b"students", b"teachers", b"admissions", b"events", b"contact"):
            self.assertIn(b'id="' + section + b'"', response.data)
        for filename in ("green-schools-campus.jpg", "mountain-lake-louise.jpg"):
            with self.subTest(image=filename):
                image = self.client.get(f"/static/images/{filename}")
                self.assertEqual(image.status_code, 200)
                self.assertEqual(image.mimetype, "image/jpeg")
                self.assertTrue(image.data.startswith(b"\xff\xd8\xff"))
                image.close()
        response = self.client.post(
            "/register",
            data={
                "name": "Jamie Park",
                "class_name": "Grade 6",
                "roll_number": "604",
                "username": "jamie",
                "email": "jamie@example.test",
                "password": "learning123",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Registration complete", response.data)
        self.assertEqual(self.sign_in("jamie", "learning123").status_code, 200)

    def test_existing_student_database_is_migrated(self):
        legacy_path = os.path.join(self.temp_dir.name, "legacy.db")
        connection = sqlite3.connect(legacy_path)
        connection.execute(
            """CREATE TABLE students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                class_name TEXT NOT NULL,
                roll_number INTEGER UNIQUE
            )"""
        )
        connection.execute(
            "INSERT INTO students (name, class_name, roll_number) VALUES (?, ?, ?)",
            ("Sam Lee", "Grade 5", 504),
        )
        connection.commit()
        connection.close()

        school_app.app.config["DATABASE"] = legacy_path
        school_app.init_db()
        with school_app.database() as db:
            student = db.execute(
                "SELECT s.name, u.username FROM students s JOIN users u ON s.user_id = u.id"
            ).fetchone()
        self.assertEqual(student["name"], "Sam Lee")
        self.assertEqual(student["username"], "student")

    def test_roles_and_dashboard_pages(self):
        self.assertEqual(self.client.get("/attendance").status_code, 302)
        self.assertEqual(self.sign_in("student", "student123").status_code, 200)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)
        self.assertEqual(self.client.get("/dashboard/student").status_code, 200)
        self.assertEqual(self.client.get("/students").status_code, 302)
        self.client.post("/logout")
        self.assertEqual(self.sign_in("teacher", "teacher123").status_code, 200)
        self.assertEqual(self.client.get("/dashboard/teacher").status_code, 200)
        self.assertEqual(self.client.get("/attendance").status_code, 200)
        self.client.post("/logout")
        self.assertEqual(self.sign_in("admin", "admin123").status_code, 200)
        self.assertEqual(self.client.get("/dashboard/admin").status_code, 200)
        self.assertEqual(self.client.get("/students").status_code, 200)

    def test_school_management_forms(self):
        self.sign_in("teacher", "teacher123")
        invalid_timetable = self.client.post(
            "/academics",
            data={
                "action": "timetable",
                "class_name": "Grade 8",
                "weekday": "Wednesday",
                "subject": "Art",
                "start_time": "12:00",
                "end_time": "11:00",
                "teacher": "Jordan Rivera",
            },
            follow_redirects=True,
        )
        self.assertIn(b"end time is after the start time", invalid_timetable.data)
        self.assertEqual(
            self.client.post(
                "/academics",
                data={
                    "action": "timetable",
                    "class_name": "Grade 8",
                    "weekday": "Wednesday",
                    "subject": "Art",
                    "start_time": "11:00",
                    "end_time": "11:50",
                    "teacher": "Jordan Rivera",
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                "/attendance",
                data={
                    "student_id": "1",
                    "attendance_date": "2026-10-20",
                    "status": "Late",
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                "/academics",
                data={
                    "action": "homework",
                    "class_name": "Grade 8",
                    "subject": "English",
                    "title": "Reading notes",
                    "due_date": "2026-10-24",
                    "details": "Write a short summary.",
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                "/results",
                data={
                    "student_id": "1",
                    "subject": "English",
                    "assessment": "Reading check",
                    "score": "9",
                    "max_score": "10",
                },
            ).status_code,
            302,
        )
        self.assertEqual(self.client.get("/academics").status_code, 200)
        self.assertIn(b"Wednesday", self.client.get("/academics").data)
        self.assertEqual(self.client.get("/results").status_code, 200)

    def test_admin_community_forms_and_validation(self):
        self.sign_in("admin", "admin123")
        invalid = self.client.post(
            "/results",
            data={
                "student_id": "1",
                "subject": "Math",
                "assessment": "Invalid score",
                "score": "12",
                "max_score": "10",
            },
            follow_redirects=True,
        )
        self.assertIn(b"Score must be between zero", invalid.data)
        self.assertEqual(
            self.client.post(
                "/community",
                data={
                    "kind": "announcement",
                    "title": "Family reading day",
                    "message": "Join us in the school library.",
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                "/community",
                data={
                    "kind": "calendar",
                    "title": "Spring fair",
                    "event_date": "2027-03-18",
                    "category": "Event",
                    "details": "A day of games and activities.",
                },
            ).status_code,
            302,
        )
        community = self.client.get("/community")
        self.assertIn(b"Family reading day", community.data)
        self.assertIn(b"Spring fair", community.data)


if __name__ == "__main__":
    unittest.main()
