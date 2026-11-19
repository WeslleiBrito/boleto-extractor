
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True)

    app_name: str = "Extrator de Boletos"
    version: str = "0.1.0"
    debug: bool = True

    supported_extensions: tuple[str, ...] = (
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
    )

    max_workers: int = 4
    dpi: int = 300

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]


settings = Settings()
