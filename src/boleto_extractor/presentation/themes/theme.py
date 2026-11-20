from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FontSpec:
    family: str
    pixelSize: int
    weight: int = 400  # 400 = normal, 500 = médio, 600 = semibold, 700 = negrito


@dataclass(frozen=True, slots=True)
class TextStyle:
    color: str
    font: FontSpec


@dataclass(frozen=True, slots=True)
class ButtonStyle:
    background: str
    backgroundHover: str
    backgroundPressed: str
    text: str
    radius: int
    font: FontSpec


@dataclass(frozen=True, slots=True)
class TableStyle:
    headerBackground: str
    headerText: str
    headerFont: FontSpec
    rowBackground: str
    rowAlternate: str
    rowHover: str
    text: str
    font: FontSpec
    border: str


@dataclass(frozen=True, slots=True)
class InputStyle:
    background: str
    border: str
    borderFocus: str
    text: str
    placeholder: str
    radius: int
    font: FontSpec


@dataclass(frozen=True, slots=True)
class StatusColors:
    """Chaves iguais aos valores de ExtractionStatus."""

    success: str
    invalid: str
    review: str
    error: str
    pending: str


@dataclass(frozen=True, slots=True)
class Theme:
    id: str
    nome: str
    escuro: bool
    background: str
    surface: str
    border: str
    accent: str
    title: TextStyle
    subtitle: TextStyle
    body: TextStyle
    mono: TextStyle
    button: ButtonStyle
    buttonSecondary: ButtonStyle
    table: TableStyle
    input: InputStyle
    status: StatusColors

    def to_qml(self) -> dict[str, Any]:
        return asdict(self)
