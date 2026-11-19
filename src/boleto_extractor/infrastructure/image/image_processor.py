from typing import cast

import cv2
import numpy as np

from boleto_extractor.core.exceptions import DocumentLoadError
from boleto_extractor.core.types import ImageArray


class ImageProcessor:
    """Realiza operações de preparação de imagens para reconhecimento."""

    def validar(self, imagem: ImageArray) -> None:
        if not isinstance(imagem, np.ndarray):
            raise DocumentLoadError(
                "A imagem precisa ser um array NumPy."
            )

        if imagem.size == 0:
            raise DocumentLoadError(
                "A imagem está vazia."
            )

        if imagem.dtype != np.uint8:
            raise DocumentLoadError(
                "A imagem precisa utilizar o tipo uint8."
            )

        if imagem.ndim != 3 or imagem.shape[2] != 3:
            raise DocumentLoadError(
                "A imagem precisa possuir três canais RGB."
            )

    def redimensionar(
        self,
        imagem: ImageArray,
        largura_maxima: int = 2000,
    ) -> ImageArray:

        self.validar(imagem)

        altura, largura = imagem.shape[:2]

        if largura <= largura_maxima:
            return imagem

        proporcao = largura_maxima / largura

        nova_altura = int(altura * proporcao)

        return cast(
    ImageArray,
    cv2.resize(
        imagem,
        (largura_maxima, nova_altura),
        interpolation=cv2.INTER_AREA,
    ),
)
    def escala_cinza(
        self,
        imagem: ImageArray,
    ) -> ImageArray:

        self.validar(imagem)

        return cast(
    ImageArray,
    cv2.cvtColor(imagem, cv2.COLOR_RGB2GRAY),
)
    def binarizar(
        self,
        imagem: ImageArray,
    ) -> ImageArray:

        cinza = self.escala_cinza(imagem)

        return cast(
            ImageArray,
    cv2.adaptiveThreshold(
        cinza,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11,
    ),
)

    def melhorar_contraste(
        self,
        imagem: ImageArray,
    ) -> ImageArray:

        cinza = self.escala_cinza(imagem)

        clahe = cv2.createCLAHE(
            clipLimit=2.0,
            tileGridSize=(8, 8),
        )

        return cast(
            ImageArray,
            clahe.apply(cinza),
        )
