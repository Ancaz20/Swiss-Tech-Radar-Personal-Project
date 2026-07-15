from typing import List

from domain.models import JobOffer
from domain.ports import JobRepository


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    def list_jobs(self, limit: int = 200, sort: str = "date") -> List[JobOffer]:
        return self.repository.list_jobs(limit=limit, sort=sort)
