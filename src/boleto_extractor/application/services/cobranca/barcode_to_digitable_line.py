from boleto_extractor.core.exceptions import BoletoValidationError


class BarcodeToDigitableLine:
    """Converte código de barras bancário em linha digitável e vice-versa."""

    def converter(self, codigo: str) -> str:
        self._validar_entrada(codigo)

        if not self._validar_dv_geral(codigo):
            raise BoletoValidationError("O dígito verificador geral é inválido.")

        campo_1 = codigo[:4] + codigo[19:24]
        campo_2 = codigo[24:34]
        campo_3 = codigo[34:44]

        return (
            campo_1 + str(self._calcular_modulo_10(campo_1))
            + campo_2 + str(self._calcular_modulo_10(campo_2))
            + campo_3 + str(self._calcular_modulo_10(campo_3))
            + codigo[4]
            + codigo[5:19]
        )

    def converter_para_codigo_barras(self, linha: str) -> str:
        """Converte uma linha digitável de 47 dígitos em código de barras de 44."""
        self._validar_linha_digitavel(linha)

        campos = (
            (linha[0:9], int(linha[9]), "primeiro"),
            (linha[10:20], int(linha[20]), "segundo"),
            (linha[21:31], int(linha[31]), "terceiro"),
        )

        for campo, dv, nome in campos:
            if self._calcular_modulo_10(campo) != dv:
                raise BoletoValidationError(
                    f"O dígito verificador do {nome} campo é inválido."
                )

        codigo = (
            linha[0:4]
            + linha[32]
            + linha[33:47]
            + linha[4:9]
            + linha[10:20]
            + linha[21:31]
        )

        self._validar_entrada(codigo)

        if not self._validar_dv_geral(codigo):
            raise BoletoValidationError("O dígito verificador geral é inválido.")

        return codigo

    def _validar_entrada(self, codigo: str) -> None:
        if not isinstance(codigo, str):
            raise BoletoValidationError("O código precisa ser uma string.")

        if len(codigo) != 44:
            raise BoletoValidationError("O código precisa possuir 44 dígitos.")

        if not codigo.isdigit():
            raise BoletoValidationError("O código deve conter somente números.")

        if codigo[3] != "9":
            raise BoletoValidationError(
                "Código de moeda incompatível com boleto em Real."
            )

    def _validar_linha_digitavel(self, linha: str) -> None:
        if not isinstance(linha, str):
            raise BoletoValidationError("A linha digitável precisa ser uma string.")

        if len(linha) != 47:
            raise BoletoValidationError("A linha digitável precisa possuir 47 dígitos.")

        if not linha.isdigit():
            raise BoletoValidationError(
                "A linha digitável deve conter somente números."
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

        resultado = 11 - soma % 11

        return 1 if resultado in (0, 10, 11) else resultado

    def _validar_dv_geral(self, codigo: str) -> bool:
        base = codigo[:4] + codigo[5:]
        return self._calcular_modulo_11(base) == int(codigo[4])
