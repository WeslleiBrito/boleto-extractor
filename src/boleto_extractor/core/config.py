import os
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

    # OpenCNPJ
    opencnpj_url: str = "https://api.opencnpj.org/{}"
    opencnpj_timeout: float = 8.0
    opencnpj_intervalo_min: float = 0.3
    opencnpj_pausa_429: float = 60.0
    cache_ttl_ok: int = 30 * 24 * 3600
    cache_ttl_nao_encontrado: int = 7 * 24 * 3600

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[3]

    @property
    def data_dir(self) -> Path:
        """Pasta de dados do usuário (sobrevive a reinstalações do app)."""
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "ExtratorBoletos"


settings = Settings()
