from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal

from boleto_extractor.domain.entities.boleto_details import BoletoDetails

BASE_FATOR_ANTIGA = date(1997, 10, 7)   # fator 1000 = 03/07/2000 ... 9999 = 21/02/2025
BASE_FATOR_NOVA = date(2025, 2, 22)     # fator 1000 = 22/02/2025 (reinício Febraban)

BANCOS: dict[str, str] = {
    "001": "Banco do Brasil", "004": "Banco do Nordeste", "021": "Banestes",
    "033": "Santander", "037": "Banpará", "041": "Banrisul", "047": "Banese",
    "070": "BRB", "077": "Inter", "104": "Caixa", "136": "Unicred",
    "208": "BTG Pactual", "212": "Original", "237": "Bradesco",
    "260": "Nubank", "290": "PagBank", "318": "BMG", "323": "Mercado Pago",
    "336": "C6 Bank", "341": "Itaú", "380": "PicPay", "389": "Mercantil",
    "403": "Cora", "422": "Safra", "633": "Rendimento", "655": "Votorantim",
    "707": "Daycoval", "745": "Citibank", "748": "Sicredi", "756": "Sicoob",
}

SEGMENTOS: dict[str, str] = {
    "1": "Prefeitura", "2": "Saneamento", "3": "Energia elétrica e gás",
    "4": "Telecomunicações", "5": "Órgão governamental",
    "6": "Empresa (CNPJ)", "7": "Multa de trânsito", "9": "Uso exclusivo do banco",
}


class BoletoParser:
    """Extrai valor, vencimento e emissor de um código de barras de 44 dígitos."""

    def __init__(self, referencia: Callable[[], date] | None = None) -> None:
        self._referencia = referencia or date.today

    # ---------------- Cobrança ----------------
    def cobranca(self, codigo: str) -> BoletoDetails:
        banco = codigo[0:3]
        observacoes: list[str] = []

        vencimento = self._data_por_fator(codigo[5:9])
        if vencimento is None:
            observacoes.append("Boleto sem vencimento definido (fator 0000).")

        valor = Decimal(int(codigo[9:19])) / 100
        if valor == 0:
            observacoes.append("Valor não informado no código (valor em aberto).")

        return BoletoDetails(
            valor=valor or None,
            vencimento=vencimento,
            banco_codigo=banco,
            banco_nome=BANCOS.get(banco, f"Banco {banco}"),
            campo_livre=codigo[19:44],
            observacoes=tuple(observacoes),
        )

    def _data_por_fator(self, fator_txt: str) -> date | None:
        fator = int(fator_txt)
        if fator < 1000:
            return None

        candidatas = [BASE_FATOR_NOVA + timedelta(days=fator - 1000)]
        candidatas.append(BASE_FATOR_ANTIGA + timedelta(days=fator))

        hoje = self._referencia()
        return min(candidatas, key=lambda d: abs((d - hoje).days))

    # ---------------- Arrecadação ----------------
    def arrecadacao(self, codigo: str) -> BoletoDetails:
        segmento = codigo[1]
        identificador = codigo[2]
        observacoes: list[str] = []

        valor: Decimal | None = None
        if identificador in "68":
            valor = (Decimal(int(codigo[4:15])) / 100) or None
        else:
            observacoes.append("Código usa quantidade de referência, não valor em reais.")

        tamanho_empresa = 8 if segmento == "6" else 4
        empresa = codigo[15:15 + tamanho_empresa]
        livre = codigo[15 + tamanho_empresa:44]

        vencimento = self._data_no_campo_livre(livre)
        if vencimento:
            observacoes.append("Vencimento estimado a partir do campo livre.")

        return BoletoDetails(
            valor=valor,
            vencimento=vencimento,
            vencimento_estimado=vencimento is not None,
            segmento=SEGMENTOS.get(segmento, f"Segmento {segmento}"),
            empresa_id=empresa,
            campo_livre=livre,
            observacoes=tuple(observacoes),
        )

    def _data_no_campo_livre(self, livre: str) -> date | None:
        hoje = self._referencia()
        limite = timedelta(days=730)

        for i in range(len(livre) - 7):
            trecho = livre[i:i + 8]
            if not trecho.startswith("20"):
                continue
            try:
                data = date(int(trecho[0:4]), int(trecho[4:6]), int(trecho[6:8]))
            except ValueError:
                continue
            if abs(data - hoje) <= limite:
                return data

        return None
