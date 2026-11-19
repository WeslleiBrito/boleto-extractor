
from pathlib import Path

import cv2
import pytest

from boleto_extractor.application.services.cobranca.barcode_to_digitable_line import (
    BarcodeToDigitableLine,
)
from boleto_extractor.infrastructure.barcode.zxing_barcode_reader import (
    ZXingBarcodeReader,
)


@pytest.mark.integration
def test_extrair_linha_digitavel_de_boleto_real() -> None:
    arquivo = Path("IMG_20261119_053700.jpg")

    imagem_bgr = cv2.imread(str(arquivo))

    assert imagem_bgr is not None, "Não foi possível carregar a imagem."

    imagem_rgb = cv2.cvtColor(imagem_bgr, cv2.COLOR_BGR2RGB)

    leitor = ZXingBarcodeReader()
    conversor = BarcodeToDigitableLine()

    codigos = leitor.ler(imagem_rgb)

    assert codigos, "Nenhum código de barras foi encontrado."

    for codigo in codigos:
        print(f"\nCódigo encontrado: {codigo.valor}")
        print(f"Formato: {codigo.formato}")

        linha = conversor.converter(codigo.valor)

        print(f"Linha digitável: {linha}")

        assert len(linha) == 47
