import json
import threading
import time
import urllib.error
import urllib.request
from typing import Any

from boleto_extractor.application.services.documento_validator import cnpj_valido, limpar
from boleto_extractor.core.config import settings
from boleto_extractor.domain.entities.beneficiario import DadosEmpresa
from boleto_extractor.infrastructure.cnpj.sqlite_cnpj_cache import (
    STATUS_NAO_ENCONTRADO,
    STATUS_OK,
    SqliteCnpjCache,
)


class OpenCnpjClient:
    """Consulta a OpenCNPJ com cache em memória + SQLite e controle de limite (429)."""

    def __init__(self, cache: SqliteCnpjCache | None = None) -> None:
        self._cache = cache or SqliteCnpjCache()
        self._memoria: dict[str, DadosEmpresa | None] = {}
        self._lock = threading.Lock()
        self._ultima = 0.0
        self._bloqueado_ate = 0.0

    def consultar(self, cnpj: str) -> DadosEmpresa | None:
        try:
            c = limpar(cnpj)
            if not cnpj_valido(c):
                return None

            with self._lock:  # serializa: o mesmo CNPJ nunca é consultado em paralelo
                if c in self._memoria:
                    return self._memoria[c]

                em_cache = self._cache.obter(c)
                if em_cache is not None:
                    self._memoria[c] = em_cache[1]
                    return em_cache[1]

                resposta = self._requisitar(c)
                if resposta is None:
                    return None  # falha transitória: não cacheia, tenta depois

                status, dados = resposta
                self._cache.salvar(c, status, dados)
                self._memoria[c] = dados
                return dados
        except Exception:
            return None

    def _requisitar(self, cnpj: str) -> tuple[str, DadosEmpresa | None] | None:
        if time.time() < self._bloqueado_ate:
            return None

        espera = settings.opencnpj_intervalo_min - (time.time() - self._ultima)
        if espera > 0:
            time.sleep(espera)

        req = urllib.request.Request(
            settings.opencnpj_url.format(cnpj),
            headers={"Accept": "application/json", "User-Agent": "ExtratorBoletos/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=settings.opencnpj_timeout) as r:
                return STATUS_OK, self._converter(json.loads(r.read().decode("utf-8")))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return STATUS_NAO_ENCONTRADO, None
            if e.code == 429:
                self._bloqueado_ate = time.time() + settings.opencnpj_pausa_429
            return None
        except Exception:
            return None
        finally:
            self._ultima = time.time()

    @staticmethod
    def _converter(j: dict[str, Any]) -> DadosEmpresa:
        def s(chave: str) -> str:
            return str(j.get(chave) or "")

        telefone = ""
        for t in j.get("telefones") or []:
            if isinstance(t, dict) and t.get("numero") and not t.get("is_fax"):
                ddd = str(t.get("ddd") or "")
                telefone = f"({ddd}) {t['numero']}" if ddd else str(t["numero"])
                break

        return DadosEmpresa(
            razao_social=s("razao_social"),
            nome_fantasia=s("nome_fantasia"),
            situacao_cadastral=s("situacao_cadastral"),
            municipio=s("municipio"),
            uf=s("uf"),
            email=s("email").lower(),
            telefone=telefone,
            cnae_principal=s("cnae_principal"),
            porte_empresa=s("porte_empresa"),
            opcao_simples=s("opcao_simples"),
            opcao_mei=s("opcao_mei"),
        )
