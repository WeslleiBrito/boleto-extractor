
from enum import StrEnum


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    INVALID = "invalid"
    REVIEW = "review"
    ERROR = "error"
