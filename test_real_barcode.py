from pathlib import Path

import pymupdf
import numpy as np

from boleto_extractor.infrastructure.barcode.zxing_barcode_reader import (
    ZXingBarcodeReader,
)

def calcular_modulo_10(numero: str) -> int:
    soma = 0
    peso = 2

    for digito in reversed(numero):
        resultado = int(digito) * peso
        soma += resultado // 10 + resultado % 10
        peso = 1 if peso == 2 else 2

    return (10 - soma % 10) % 10

arquivo = Path("IMG_20261118_204625_.jpg")

imagem = pymupdf.Pixmap(str(arquivo))

reader = ZXingBarcodeReader()

# Carregamento da imagem usando OpenCV
import cv2

imagem_array = cv2.imread(str(arquivo))
imagem_rgb = cv2.cvtColor(imagem_array, cv2.COLOR_BGR2RGB)

resultados = reader.ler(imagem_rgb)

codigo = resultados[0].valor

# DV geral: posição 4 (índice 3)
base = codigo[:3] + codigo[4:]
dv_calculado = calcular_modulo_10(base)

print(f"DV informado: {codigo[3]}")
print(f"DV calculado: {dv_calculado}")
print(f"DV válido: {codigo[3] == str(dv_calculado)}")

for resultado in resultados:
    print(f"Código: {resultado.valor}")
    print(f"Formato: {resultado.formato}")
    print(f"Quantidade de dígitos: {len(resultado.valor)}")