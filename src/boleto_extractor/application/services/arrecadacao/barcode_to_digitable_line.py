
from boleto_extractor.core.exceptions import BoletoValidationError


class BarcodeToDigitableLine:
    """Converte código de barras de arrecadação em linha digitável."""

    def converter(self, codigo: str) -> str:
        self._validar_entrada(codigo)

        modulo = self._obter_modulo(codigo)

        if not self._validar_dv_geral(codigo, modulo):
            raise BoletoValidationError(
                "O dígito verificador geral do código de barras é inválido."
            )

        grupos = [
            codigo[i : i + 11]
            for i in range(0, 44, 11)
        ]

        grupos_formatados = [
            grupo + str(self._calcular_dv(grupo, modulo))
            for grupo in grupos
        ]

        return "".join(grupos_formatados)

    def _validar_entrada(self, codigo: str) -> None:
        if not isinstance(codigo, str):
            raise BoletoValidationError(
                "O código de barras precisa ser uma string."
            )

        if len(codigo) != 44:
            raise BoletoValidationError(
                "O código de barras precisa possuir 44 dígitos."
            )

        if not codigo.isdigit():
            raise BoletoValidationError(
                "O código de barras deve conter somente números."
            )

        if not codigo.startswith("8"):
            raise BoletoValidationError(
                "O código informado não é de arrecadação."
            )

        if codigo[2] not in "6789":
            raise BoletoValidationError(
                "Identificador de valor ou referência inválido."
            )

    def _obter_modulo(self, codigo: str) -> int:
        return 10 if codigo[2] in "67" else 11

    def _calcular_dv(self, numero: str, modulo: int) -> int:
        if modulo == 10:
            return self._calcular_modulo_10(numero)

        return self._calcular_modulo_11(numero)

    def _calcular_modulo_10(self, numero: str) -> int:
        soma = 0
        peso = 2

        for digito in reversed(numero):
            produto = int(digito) * peso
            soma += produto // 10 + produto % 10
            peso = 1 if peso == 2 else 2

        return (10 - soma % 10) % 10

    def _calcular_modulo_11(self, numero: str) -> int:
        soma = 0
        peso = 2

        for digito in reversed(numero):
            soma += int(digito) * peso
            peso = 2 if peso == 9 else peso + 1

        resto = soma % 11

        if resto in (0, 1):
            return 0

        if resto == 10:
            return 1

        return 11 - resto

    def _validar_dv_geral(
        self,
        codigo: str,
        modulo: int,
    ) -> bool:
        base = codigo[:3] + codigo[4:]
        dv_informado = int(codigo[3])

        return self._calcular_dv(base, modulo) == dv_informado
