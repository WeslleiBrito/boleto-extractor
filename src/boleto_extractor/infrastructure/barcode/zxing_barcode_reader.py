
import cv2
import numpy as np
import zxingcpp

from boleto_extractor.application.ports.barcode_reader import (
    BarcodeReading,
)
from boleto_extractor.core.exceptions import BarcodeReadingError
from boleto_extractor.core.types import ImageArray


class ZXingBarcodeReader:
    """Implementação do leitor de códigos de barras utilizando ZXing-C++."""

    def __init__(
        self,
        try_rotate: bool = True,
        try_downscale: bool = True,
        try_invert: bool = True,
    ) -> None:
        self._formats = zxingcpp.barcode_formats_from_str("ITF, Code128")
        self._try_rotate = try_rotate
        self._try_downscale = try_downscale
        self._try_invert = try_invert

    def ler(self, imagem: ImageArray) -> tuple[BarcodeReading, ...]:
        self._validar_imagem(imagem)

        try:
            imagem_bgr = cv2.cvtColor(imagem, cv2.COLOR_RGB2BGR)
            imagem_bgr = np.ascontiguousarray(imagem_bgr)

            codigos = zxingcpp.read_barcodes(
                imagem_bgr,
                formats=self._formats,
                try_rotate=self._try_rotate,
                try_downscale=self._try_downscale,
                try_invert=self._try_invert,
            )

            return tuple(
                BarcodeReading(
                    valor=codigo.text,
                    formato=str(codigo.format),
                )
                for codigo in codigos
                if codigo.valid and codigo.text
            )

        except Exception as exc:
            raise BarcodeReadingError(
                "Não foi possível realizar a leitura do código de barras."
            ) from exc

    def _validar_imagem(self, imagem: ImageArray) -> None:
        if not isinstance(imagem, np.ndarray):
            raise BarcodeReadingError(
                "A imagem precisa ser um array NumPy."
            )

        if imagem.size == 0:
            raise BarcodeReadingError("A imagem está vazia.")

        if imagem.dtype != np.uint8:
            raise BarcodeReadingError(
                "A imagem precisa utilizar o tipo uint8."
            )

        if imagem.ndim != 3 or imagem.shape[2] != 3:
            raise BarcodeReadingError(
                "A imagem precisa possuir três canais RGB."
            )
