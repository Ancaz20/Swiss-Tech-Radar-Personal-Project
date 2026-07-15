import os
import sqlite3
import tempfile
import unittest

import ingest


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(dir=".")
        self.db_path = os.path.join(self.tmpdir, "test.db")
        ingest.DB_PATH = self.db_path
        self.conn = ingest.get_connection()

    def tearDown(self):
        self.conn.close()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.tmpdir)

    def test_extract_skills_is_case_insensitive_and_deduplicated(self):
        text = "We need Python, Docker and more python experience"
        self.assertEqual(ingest.extract_skills(text), ["python", "docker"])

    def test_extract_skills_matches_extended_keywords(self):
        text = "Looking for a Go engineer with Linux and PostgreSQL experience"
        self.assertEqual(ingest.extract_skills(text), ["go", "linux", "postgresql"])

    def test_looks_like_junior_role_matches_entry_level_titles(self):
        job = {"title": "Graduate Software Developer", "description": "Great place for junior talent"}
        self.assertTrue(ingest.looks_like_junior_role(job))

    def test_looks_like_junior_role_rejects_senior_titles(self):
        job = {"title": "Senior Staff Software Engineer", "description": "Lead the platform"}
        self.assertFalse(ingest.looks_like_junior_role(job))

    def test_matches_stack_focus_filters_by_requested_stack(self):
        ingest.STACK_FOCUS = "python"
        self.assertTrue(ingest.matches_stack_focus("We need a Python developer"))
        self.assertFalse(ingest.matches_stack_focus("We need a Java developer"))
        ingest.STACK_FOCUS = None

    def test_matches_stack_focus_reads_environment_variable(self):
        os.environ["STACK_FOCUS"] = "java"
        self.assertTrue(ingest.matches_stack_focus("We need a Java developer"))
        self.assertFalse(ingest.matches_stack_focus("We need a Python developer"))
        del os.environ["STACK_FOCUS"]

    def test_build_search_query_includes_stack_focus(self):
        ingest.STACK_FOCUS = "python"
        self.assertEqual(ingest.build_search_query("junior developer"), "junior developer python")
        ingest.STACK_FOCUS = None

    def test_reset_database_clears_existing_rows(self):
        ingest.save_job(self.conn, {"id": "job-1", "title": "Junior Dev", "company": {"display_name": "Acme"}, "location": {"display_name": "Zurich"}, "salary_min": None, "salary_max": None, "contract_type": None, "created": None, "redirect_url": None, "description": "Python"}, ["python"])
        ingest.reset_database(self.conn)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0], 0)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM job_skills").fetchone()[0], 0)

    def test_save_job_persists_job_and_skill_links(self):
        job = {
            "id": "job-1",
            "title": "Junior Python Developer",
            "company": {"display_name": "Acme"},
            "location": {"display_name": "Zurich, Switzerland"},
            "salary_min": 70000,
            "salary_max": 90000,
            "contract_type": "permanent",
            "created": "2024-01-01",
            "redirect_url": "https://example.com/job/1",
            "description": "Work with Python and Docker.",
        }

        ingest.save_job(self.conn, job, ["python", "docker"])

        row = self.conn.execute("SELECT adzuna_id, title, company FROM jobs WHERE adzuna_id = ?", ("job-1",)).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "job-1")
        self.assertEqual(row[1], "Junior Python Developer")

        skill_ids = self.conn.execute("SELECT skill_id FROM job_skills JOIN jobs ON jobs.id = job_skills.job_id WHERE jobs.adzuna_id = ?", ("job-1",)).fetchall()
        self.assertEqual(len(skill_ids), 2)


if __name__ == "__main__":
    unittest.main()
