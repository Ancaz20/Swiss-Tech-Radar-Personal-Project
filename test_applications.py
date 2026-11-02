import importlib
import os
import sqlite3
import tempfile
import unittest

webapp = importlib.import_module("app.app")


class ApplicationTrackingTests(unittest.TestCase):
    def setUp(self):
        self.original_db_path = webapp.DB_PATH
        self.original_database_url = os.environ.pop("DATABASE_URL", None)
        self.tmpdir = tempfile.TemporaryDirectory(dir=".")
        webapp.DB_PATH = os.path.join(self.tmpdir.name, "test.db")
        conn = sqlite3.connect(webapp.DB_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        with open(os.path.join(os.path.dirname(__file__), "schema.sql"), encoding="utf-8") as schema:
            conn.executescript(schema.read())
        conn.execute(
            """INSERT INTO jobs (adzuna_id, title, company, location, created, redirect_url, description)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("test-job-1", "Junior Java Developer", "Example AG", "Basel", "2026-10-01",
             "https://example.com/job/1", "Java, Spring and PostgreSQL"),
        )
        conn.commit()
        conn.close()
        webapp.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = webapp.app.test_client()

    def tearDown(self):
        webapp.DB_PATH = self.original_db_path
        if self.original_database_url is not None:
            os.environ["DATABASE_URL"] = self.original_database_url
        self.tmpdir.cleanup()

    def test_match_score_returns_overlap_and_skills(self):
        score, matched = webapp.calculate_match_score(
            "java, spring, kubernetes",
            {"java", "spring", "python"},
        )
        self.assertEqual(score, 67)
        self.assertEqual(matched, ["java", "spring"])

    def test_save_application_and_update_notes(self):
        webapp.save_application(1, "saved", "Contactar con RR. HH.")
        webapp.save_application(1, "interview", "Entrevista el viernes")
        items = webapp.load_applications()
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["status"], "interview")
        self.assertEqual(items[0]["notes"], "Entrevista el viernes")

    def test_language_requirement_detects_english_c1(self):
        self.assertEqual(
            webapp.detect_language_requirements("Fluent English C1 required"),
            {"english": "C1"},
        )

    def test_language_score_rewards_profile_level(self):
        old = os.environ.get("PROFILE_LANGUAGES")
        os.environ["PROFILE_LANGUAGES"] = "english:C1"
        try:
            score, details, known = webapp.calculate_language_score("English C1 required")
            self.assertEqual(score, 100)
            self.assertTrue(known)
            self.assertIn("english", details[0])
        finally:
            if old is None:
                os.environ.pop("PROFILE_LANGUAGES", None)
            else:
                os.environ["PROFILE_LANGUAGES"] = old

    def test_full_match_includes_all_four_factors(self):
        job = {
            "title": "Junior Java Developer Internship",
            "description": "Java, Spring. English C1 required.",
            "skills": "java, spring",
            "contract_type": "internship",
        }
        result = webapp.calculate_job_match(job)
        self.assertEqual(set(result["breakdown"]), {"skills", "languages", "experience", "contract"})
        self.assertEqual(result["breakdown"]["languages"], 100)
        self.assertEqual(result["breakdown"]["experience"], 100)
        self.assertEqual(result["breakdown"]["contract"], 100)
        self.assertGreaterEqual(result["score"], 80)

    def test_unspecified_language_is_not_scored_as_a_failure(self):
        score, details, known = webapp.calculate_language_score("No language level mentioned")
        self.assertEqual(score, 75)
        self.assertFalse(known)

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            webapp.save_application(1, "unknown", "")

    def test_missing_job_is_rejected(self):
        with self.assertRaises(LookupError):
            webapp.save_application(999, "saved", "")

    def test_dashboard_lists_saved_application(self):
        webapp.save_application(1, "saved", "")
        response = self.client.get("/applications")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Junior Java Developer", response.data)

    def test_update_route_requires_csrf(self):
        response = self.client.post("/applications/1", data={"status": "saved"})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
