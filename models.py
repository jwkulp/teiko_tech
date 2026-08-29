from dataclasses import dataclass
from enum import Enum


class Response(Enum):
    YES = 'yes'
    NO = 'no'
    NOT_APPL = 'n/a'


@dataclass(frozen=True)
class Subject:
    subject_id: str
    project: str
    condition: str
    sex: str
    age: int


@dataclass(frozen=True)
class Sample:
    sample_id: str
    subject_id: str
    sample_type: str
    time_from_treatment: int
    treatment: str
    responded: Response
