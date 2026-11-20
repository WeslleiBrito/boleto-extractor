from boleto_extractor.application.services.arrecadacao.barcode_to_digitable_line import (
    BarcodeToDigitableLine as ArrecadacaoConverter,
)
from boleto_extractor.application.services.cobranca.barcode_to_digitable_line import (
    BarcodeToDigitableLine as CobrancaConverter,
)
from boleto_extractor.core.exceptions import BoletoValidationError


class CodeNormalizer:
    """Converte qualquer entrada (44, 47 ou 48 dígitos) para o código de barras de 44."""

    def __init__(
        self,
        cobranca: CobrancaConverter | None = None,
        arrecadacao: ArrecadacaoConverter | None = None,
    ) -> None:
        self._cobranca = cobranca or CobrancaConverter()
        self._arrecadacao = arrecadacao or ArrecadacaoConverter()

    def para_codigo_barras(self, texto: str) -> str:
        digitos = "".join(c for c in texto if c.isdigit())
        tamanho = len(digitos)

        if tamanho == 44:
            return digitos

        if tamanho == 47:
            if digitos.startswith("8"):
                raise BoletoValidationError("Linha de 47 dígitos não pode começar com 8.")
            codigo = (
                digitos[0:4] + digitos[32] + digitos[33:47]
                + digitos[4:9] + digitos[10:20] + digitos[21:31]
            )
            self._conferir(self._cobranca.converter(codigo), digitos)
            return codigo

        if tamanho == 48:
            if not digitos.startswith("8"):
                raise BoletoValidationError("Linha de arrecadação deve começar com 8.")
            codigo = digitos[0:11] + digitos[12:23] + digitos[24:35] + digitos[36:47]
            self._conferir(self._arrecadacao.converter(codigo), digitos)
            return codigo

        if tamanho == 0:
            raise BoletoValidationError("Nenhum número informado.")

        raise BoletoValidationError(
            f"Código com {tamanho} dígitos. Esperado 44, 47 ou 48."
        )

    @staticmethod
    def _conferir(recalculada: str, informada: str) -> None:
        if recalculada != informada:
            raise BoletoValidationError(
                "Dígito verificador de campo não confere. Verifique a digitação."
            )
