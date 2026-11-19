
from boleto_extractor.core.exceptions import BoletoValidationError


class BarcodeToDigitableLine:
    """Converte código de barras bancário em linha digitável."""

    def converter(self, codigo: str) -> str:
        self._validar_entrada(codigo)

        if not self._validar_dv_geral(codigo):
            raise BoletoValidationError(
                "O dígito verificador geral é inválido."
            )

        campo_1 = codigo[:4] + codigo[19:24]
        campo_2 = codigo[24:34]
        campo_3 = codigo[34:44]

        dv_1 = self._calcular_modulo_10(campo_1)
        dv_2 = self._calcular_modulo_10(campo_2)
        dv_3 = self._calcular_modulo_10(campo_3)

        return (
            campo_1 + str(dv_1)
            + campo_2 + str(dv_2)
            + campo_3 + str(dv_3)
            + codigo[4]
            + codigo[5:19]
        )

    def _validar_entrada(self, codigo: str) -> None:
        if not isinstance(codigo, str):
            raise BoletoValidationError(
                "O código precisa ser uma string."
            )

        if len(codigo) != 44:
            raise BoletoValidationError(
                "O código precisa possuir 44 dígitos."
            )

        if not codigo.isdigit():
            raise BoletoValidationError(
                "O código deve conter somente números."
            )

        if codigo[3] != "9":
            raise BoletoValidationError(
                "Código de moeda incompatível com boleto em Real."
            )

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
        resultado = 11 - resto

        if resultado in (0, 10, 11):
            return 1

        return resultado

    def _validar_dv_geral(self, codigo: str) -> bool:
        base = codigo[:4] + codigo[5:]
        dv_calculado = self._calcular_modulo_11(base)

        return dv_calculado == int(codigo[4])
