from __future__ import annotations

import json
import shutil
import threading
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QSettings, QStandardPaths, QUrl, Signal, Slot

KEYRING_SERVICO = "BoletoExtractor-MySQL"

PADROES: dict[str, Any] = {
    "bq_ativo": False,
    "bq_credencial": "",
    "bq_projeto": "",
    "bq_tabela": "basedosdados.br_me_cnpj.estabelecimentos",
    "bq_limite_gb": 5,
    "db_ativo": False,
    "db_host": "localhost",
    "db_porta": 3306,
    "db_banco": "",
    "db_usuario": "",
    "db_ssl": False,
}


def _prop(tipo: type, chave: str, sinal: Signal) -> Property:
    def getter(self: "SettingsViewModel"):
        return self._dados[chave]

    def setter(self: "SettingsViewModel", valor) -> None:
        if self._dados[chave] != valor:
            self._dados[chave] = valor
            sinal.__get__(self).emit()

    return Property(tipo, getter, setter, notify=sinal)


def _caminho(url: QUrl | str) -> Path:
    if isinstance(url, QUrl):
        return Path(url.toLocalFile())
    texto = str(url)
    return Path(QUrl(texto).toLocalFile() if texto.startswith("file:") else texto)


class SettingsViewModel(QObject):
    alterado = Signal()
    testeConcluido = Signal(str, bool, str)  # tipo ("bq" | "db"), ok, mensagem

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._qs = QSettings()
        self._dados: dict[str, Any] = {}
        self._senha = ""
        self._carregar()

    # ---------------- Propriedades expostas ao QML ----------------
    bqAtivo = _prop(bool, "bq_ativo", alterado)
    bqCredencial = _prop(str, "bq_credencial", alterado)
    bqProjeto = _prop(str, "bq_projeto", alterado)
    bqTabela = _prop(str, "bq_tabela", alterado)
    bqLimiteGb = _prop(int, "bq_limite_gb", alterado)
    dbAtivo = _prop(bool, "db_ativo", alterado)
    dbHost = _prop(str, "db_host", alterado)
    dbPorta = _prop(int, "db_porta", alterado)
    dbBanco = _prop(str, "db_banco", alterado)
    dbUsuario = _prop(str, "db_usuario", alterado)
    dbSsl = _prop(bool, "db_ssl", alterado)

    def _get_senha(self) -> str:
        return self._senha

    def _set_senha(self, valor: str) -> None:
        self._senha = valor

    dbSenha = Property(str, _get_senha, _set_senha, notify=alterado)

    def _get_senha_salva(self) -> bool:
        return bool(self.senha_mysql())

    dbSenhaSalva = Property(bool, _get_senha_salva, notify=alterado)

    # ---------------- Persistência ----------------
    def _carregar(self) -> None:
        for chave, padrao in PADROES.items():
            self._dados[chave] = self._qs.value(chave, padrao, type=type(padrao))

    def senha_mysql(self) -> str:
        if self._senha:
            return self._senha
        try:
            import keyring
            return keyring.get_password(KEYRING_SERVICO, self._dados["db_usuario"] or "_") or ""
        except Exception:
            return ""

    def valores(self) -> dict[str, Any]:
        return dict(self._dados)

    @Slot(result=bool)
    def salvar(self) -> bool:
        for chave, valor in self._dados.items():
            self._qs.setValue(chave, valor)
        self._qs.sync()

        if self._senha:
            try:
                import keyring
                keyring.set_password(KEYRING_SERVICO, self._dados["db_usuario"] or "_", self._senha)
                self._senha = ""
            except Exception as exc:
                self.testeConcluido.emit("db", False, f"Senha não salva no cofre: {exc}")
                return False

        self.alterado.emit()
        return True

    # ---------------- Credencial BigQuery ----------------
    @Slot("QVariant")
    def importarCredencial(self, url) -> None:
        origem = _caminho(url)
        try:
            dados = json.loads(origem.read_text(encoding="utf-8"))
            if dados.get("type") != "service_account":
                raise ValueError("o arquivo não é uma chave de conta de serviço")

            pasta = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
            pasta.mkdir(parents=True, exist_ok=True)
            destino = pasta / "bigquery_credencial.json"
            shutil.copyfile(origem, destino)

            self.bqCredencial = str(destino)
            if not self._dados["bq_projeto"] and dados.get("project_id"):
                self.bqProjeto = dados["project_id"]
            self.testeConcluido.emit("bq", True, f"Credencial importada: {dados.get('client_email', '')}")
        except Exception as exc:
            self.testeConcluido.emit("bq", False, f"Falha ao importar credencial: {exc}")

    @Slot()
    def removerCredencial(self) -> None:
        caminho = Path(self._dados["bq_credencial"]) if self._dados["bq_credencial"] else None
        if caminho and caminho.exists():
            caminho.unlink(missing_ok=True)
        self.bqCredencial = ""
        self.testeConcluido.emit("bq", True, "Credencial removida")

    # ---------------- Testes de conexão (em thread) ----------------
    @Slot()
    def testarBigQuery(self) -> None:
        cfg = self.valores()
        threading.Thread(target=self._testar_bq, args=(cfg,), daemon=True).start()

    def _testar_bq(self, cfg: dict[str, Any]) -> None:
        try:
            from google.cloud import bigquery
            from google.oauth2 import service_account

            if not cfg["bq_credencial"]:
                raise ValueError("importe a credencial primeiro")

            cred = service_account.Credentials.from_service_account_file(cfg["bq_credencial"])
            cliente = bigquery.Client(credentials=cred, project=cfg["bq_projeto"] or cred.project_id)
            job = cliente.query(
                f"SELECT cnpj_basico FROM `{cfg['bq_tabela']}` LIMIT 1",
                job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False),
            )
            gb = (job.total_bytes_processed or 0) / 1024**3
            limite = cfg["bq_limite_gb"]
            ok = gb <= limite
            self.testeConcluido.emit(
                "bq", ok,
                f"Conectado. Consulta estimada: {gb:.2f} GB (limite {limite} GB)"
                + ("" if ok else " — acima do limite!"),
            )
        except ImportError:
            self.testeConcluido.emit("bq", False, "Instale: pip install google-cloud-bigquery")
        except Exception as exc:
            self.testeConcluido.emit("bq", False, f"Erro: {exc}")

    # ---------------- Teste de consulta real de CNPJ ----------------
    @Slot(str)
    def testarConsultaCnpj(self, cnpj: str) -> None:
        cfg = self.valores()
        cfg["bq_ativo"] = True  # testa mesmo com o checkbox desmarcado
        self.testeConcluido.emit("bq", True, f"Consultando {cnpj}… (pode levar alguns segundos)")
        threading.Thread(target=self._testar_cnpj, args=(cfg, cnpj), daemon=True).start()

    def _testar_cnpj(self, cfg: dict[str, Any], cnpj: str) -> None:
        try:
            from boleto_extractor.infrastructure.cnpj.bigquery_cnpj_client import BigQueryCnpjClient

            if not cfg["bq_credencial"]:
                raise ValueError("importe a credencial primeiro")

            cliente = BigQueryCnpjClient(lambda: cfg)
            inicio = time.perf_counter()
            dados = cliente.consultar(cnpj)
            segundos = time.perf_counter() - inicio

            if dados is None:
                self.testeConcluido.emit(
                    "bq", False, f"CNPJ não encontrado na base ({segundos:.1f}s). Confira os 14 dígitos."
                )
                return

            self.testeConcluido.emit(
                "bq", True,
                f"✔ {dados.razao_social or '(sem razão social)'}"
                f"{' — ' + dados.nome_fantasia if dados.nome_fantasia else ''}\n"
                f"Situação: {dados.situacao} | UF: {dados.uf} | {segundos:.1f}s",
            )
        except ImportError:
            self.testeConcluido.emit("bq", False, "Instale: pip install google-cloud-bigquery")
        except Exception as exc:
            texto = str(exc)
            if "bytesBilledLimitExceeded" in texto or "bytes billed" in texto.lower():
                texto = "Consulta passou do limite de GB. Aumente o limite e teste de novo."
            self.testeConcluido.emit("bq", False, f"Erro: {texto}")

    @Slot()
    def testarMySQL(self) -> None:
        cfg = self.valores()
        senha = self.senha_mysql()
        threading.Thread(target=self._testar_db, args=(cfg, senha), daemon=True).start()

    def _testar_db(self, cfg: dict[str, Any], senha: str) -> None:
        try:
            import pymysql

            conexao = pymysql.connect(
                host=cfg["db_host"],
                port=int(cfg["db_porta"]),
                user=cfg["db_usuario"],
                password=senha,
                database=cfg["db_banco"] or None,
                ssl={"ssl": {}} if cfg["db_ssl"] else None,
                connect_timeout=5,
            )
            with conexao, conexao.cursor() as cur:
                cur.execute("SELECT VERSION()")
                versao = cur.fetchone()[0]
            self.testeConcluido.emit("db", True, f"Conectado ao MySQL {versao}")
        except ImportError:
            self.testeConcluido.emit("db", False, "Instale: pip install pymysql")
        except Exception as exc:
            self.testeConcluido.emit("db", False, f"Erro: {exc}")

    # ---------------- Exportar / importar (sem senha) ----------------
    @Slot("QVariant")
    def exportar(self, url) -> None:
        try:
            dados = {k: self._qs.value(k, v, type=type(v)) for k, v in PADROES.items()}
            dados.pop("bq_credencial", None)
            _caminho(url).write_text(json.dumps(dados, indent=2, ensure_ascii=False), encoding="utf-8")
            self.testeConcluido.emit("db", True, "Configuração exportada (sem senha e sem credencial)")
        except Exception as exc:
            self.testeConcluido.emit("db", False, f"Falha ao exportar: {exc}")

    @Slot("QVariant")
    def importar(self, url) -> None:
        try:
            dados = json.loads(_caminho(url).read_text(encoding="utf-8"))
            for chave, padrao in PADROES.items():
                if chave in dados and chave != "bq_credencial":
                    self._dados[chave] = type(padrao)(dados[chave])
            self.alterado.emit()
            self.testeConcluido.emit("db", True, "Configuração importada — clique em Salvar")
        except Exception as exc:
            self.testeConcluido.emit("db", False, f"Falha ao importar: {exc}")
