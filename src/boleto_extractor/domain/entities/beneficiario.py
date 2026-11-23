from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DadosEmpresa:
    """Dados públicos do CNPJ (OpenCNPJ). Campos vazios quando indisponíveis."""

    razao_social: str = ""
    nome_fantasia: str = ""
    situacao_cadastral: str = ""
    municipio: str = ""
    uf: str = ""
    email: str = ""
    telefone: str = ""
    cnae_principal: str = ""
    porte_empresa: str = ""
    opcao_simples: str = ""
    opcao_mei: str = ""


@dataclass(frozen=True, slots=True)
class Beneficiario:
    documento: str          # sem máscara
    tipo: str               # "CNPJ" ou "CPF"
    empresa: DadosEmpresa | None = None
    confirmado_pelo_codigo: bool = False  # raiz do CNPJ bate com o código (segmento 6)

    @property
    def documento_formatado(self) -> str:
        d = self.documento
        if self.tipo == "CNPJ" and len(d) == 14:
            return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
        if self.tipo == "CPF" and len(d) == 11:
            return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
        return d

    @property
    def nome(self) -> str:
        if not self.empresa:
            return ""
        return self.empresa.razao_social or self.empresa.nome_fantasia
