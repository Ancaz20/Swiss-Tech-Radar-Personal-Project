from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(slots=True)
class JobOffer:
    id: Optional[int]
    title: str
    company: str
    location: str
    salary_min: Optional[float]
    salary_max: Optional[float]
    contract_type: Optional[str]
    created: str
    redirect_url: Optional[str]
    skills: str = ""
    skill_count: int = 0

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
