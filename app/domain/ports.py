from abc import ABC, abstractmethod
from typing import List

from domain.models import JobOffer


class JobRepository(ABC):
    @abstractmethod
    def list_jobs(self, limit: int = 200, sort: str = "date") -> List[JobOffer]:
        raise NotImplementedError
