
from enum import StrEnum


class BoletoType(StrEnum):
    BANK_SLIP = "bank_slip"
    ARRECADACAO = "arrecadacao"
    UNKNOWN = "unknown"
