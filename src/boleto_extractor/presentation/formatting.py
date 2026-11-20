from datetime import date
from decimal import Decimal


def formatar_linha(linha: str) -> str:
    """Formata a linha digitável no padrão visual dos boletos."""
    if len(linha) == 47:
        return (
            f"{linha[0:5]}.{linha[5:10]} {linha[10:15]}.{linha[15:21]} "
            f"{linha[21:26]}.{linha[26:32]} {linha[32]} {linha[33:]}"
        )
    if len(linha) == 48:
        return " ".join(f"{linha[i:i + 11]}-{linha[i + 11]}" for i in range(0, 48, 12))
    return linha


def formatar_valor(valor: Decimal | None) -> str:
    if valor is None:
        return ""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


def formatar_valor_csv(valor: Decimal | None) -> str:
    return "" if valor is None else f"{valor:.2f}".replace(".", ",")


def formatar_data(data: date | None, estimada: bool = False) -> str:
    if data is None:
        return ""
    texto = data.strftime("%d/%m/%Y")
    return f"~{texto}" if estimada else texto
