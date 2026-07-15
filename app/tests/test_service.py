from application.services import JobService
from domain.models import JobOffer


class FakeRepository:
    def __init__(self) -> None:
        self.calls = []

    def list_jobs(self, limit: int = 200, sort: str = "date"):
        self.calls.append((limit, sort))
        return [
            JobOffer(
                id=1,
                title="Python Developer",
                company="Acme",
                location="Zurich",
                salary_min=None,
                salary_max=None,
                contract_type=None,
                created="2026-01-01",
                redirect_url=None,
                skills="Python",
                skill_count=1,
            )
        ]


def test_job_service_delegates_to_repository():
    repository = FakeRepository()
    service = JobService(repository)

    jobs = service.list_jobs(limit=10, sort="company")

    assert repository.calls == [(10, "company")]
    assert jobs[0].title == "Python Developer"
