from boleto_extractor.presentation.themes.theme import (
    ButtonStyle,
    FontSpec,
    InputStyle,
    StatusColors,
    TableStyle,
    TextStyle,
    Theme,
)

SYSTEM_ID = "system"

SANS = "Segoe UI"
MONO = "Consolas"
DISPLAY = "Bahnschrift"


def _f(size: int, weight: int = 400, family: str = SANS) -> FontSpec:
    return FontSpec(family=family, pixelSize=size, weight=weight)


CLARO = Theme(
    id="claro",
    nome="Claro",
    escuro=False,
    background="#F5F6F8",
    surface="#FFFFFF",
    border="#E1E4EA",
    accent="#2563EB",
    title=TextStyle(color="#111827", font=_f(22, 700)),
    subtitle=TextStyle(color="#6B7280", font=_f(13)),
    body=TextStyle(color="#1F2937", font=_f(14)),
    mono=TextStyle(color="#111827", font=_f(14, 500, MONO)),
    button=ButtonStyle(
        background="#2563EB", backgroundHover="#1D4ED8", backgroundPressed="#1E40AF",
        text="#FFFFFF", radius=8, font=_f(14, 600),
    ),
    buttonSecondary=ButtonStyle(
        background="#EEF1F5", backgroundHover="#E2E6EC", backgroundPressed="#D5DAE2",
        text="#1F2937", radius=8, font=_f(14, 500),
    ),
    table=TableStyle(
        headerBackground="#F0F2F5", headerText="#4B5563", headerFont=_f(12, 700),
        rowBackground="#FFFFFF", rowAlternate="#FAFBFC", rowHover="#EEF4FF",
        text="#1F2937", font=_f(13), border="#E5E7EB",
    ),
    input=InputStyle(
        background="#FFFFFF", border="#D1D5DB", borderFocus="#2563EB",
        text="#111827", placeholder="#9CA3AF", radius=8, font=_f(14),
    ),
    status=StatusColors(
        success="#16A34A", invalid="#DC2626", review="#D97706",
        error="#7C3AED", pending="#6B7280",
    ),
)

ESCURO = Theme(
    id="escuro",
    nome="Escuro",
    escuro=True,
    background="#0F1115",
    surface="#171A21",
    border="#262B35",
    accent="#3B82F6",
    title=TextStyle(color="#F3F4F6", font=_f(22, 700)),
    subtitle=TextStyle(color="#9CA3AF", font=_f(13)),
    body=TextStyle(color="#E5E7EB", font=_f(14)),
    mono=TextStyle(color="#F9FAFB", font=_f(14, 500, MONO)),
    button=ButtonStyle(
        background="#3B82F6", backgroundHover="#2563EB", backgroundPressed="#1D4ED8",
        text="#FFFFFF", radius=8, font=_f(14, 600),
    ),
    buttonSecondary=ButtonStyle(
        background="#232833", backgroundHover="#2C3240", backgroundPressed="#363D4D",
        text="#E5E7EB", radius=8, font=_f(14, 500),
    ),
    table=TableStyle(
        headerBackground="#1D212A", headerText="#9CA3AF", headerFont=_f(12, 700),
        rowBackground="#171A21", rowAlternate="#1A1E26", rowHover="#1F2A3D",
        text="#E5E7EB", font=_f(13), border="#262B35",
    ),
    input=InputStyle(
        background="#11141A", border="#2E3442", borderFocus="#3B82F6",
        text="#F3F4F6", placeholder="#6B7280", radius=8, font=_f(14),
    ),
    status=StatusColors(
        success="#22C55E", invalid="#EF4444", review="#F59E0B",
        error="#A78BFA", pending="#6B7280",
    ),
)

LARANJA_PRETO = Theme(
    id="laranja_preto",
    nome="Laranja & Preto",
    escuro=True,
    background="#0A0A0A",
    surface="#141414",
    border="#2B1C0D",
    accent="#FF7A00",
    title=TextStyle(color="#FF7A00", font=_f(24, 700, DISPLAY)),
    subtitle=TextStyle(color="#B8A089", font=_f(13, 400, DISPLAY)),
    body=TextStyle(color="#F2E8DE", font=_f(14)),
    mono=TextStyle(color="#FFB366", font=_f(14, 600, MONO)),
    button=ButtonStyle(
        background="#FF7A00", backgroundHover="#FF8F26", backgroundPressed="#E06A00",
        text="#0A0A0A", radius=4, font=_f(14, 700, DISPLAY),
    ),
    buttonSecondary=ButtonStyle(
        background="#1E1E1E", backgroundHover="#2A2016", backgroundPressed="#3A2A18",
        text="#FF9A3D", radius=4, font=_f(14, 600, DISPLAY),
    ),
    table=TableStyle(
        headerBackground="#FF7A00", headerText="#0A0A0A", headerFont=_f(12, 700, DISPLAY),
        rowBackground="#141414", rowAlternate="#191512", rowHover="#2A1A0A",
        text="#F2E8DE", font=_f(13), border="#2B1C0D",
    ),
    input=InputStyle(
        background="#0F0F0F", border="#3A2A18", borderFocus="#FF7A00",
        text="#F2E8DE", placeholder="#7A6652", radius=4, font=_f(14),
    ),
    status=StatusColors(
        success="#7CD992", invalid="#FF4D4D", review="#FFC14D",
        error="#C084FC", pending="#7A6652",
    ),
)

OCEANO = Theme(
    id="oceano",
    nome="Oceano",
    escuro=True,
    background="#0B1724",
    surface="#102233",
    border="#1B3550",
    accent="#22D3EE",
    title=TextStyle(color="#E0F7FF", font=_f(22, 600)),
    subtitle=TextStyle(color="#7FA7C2", font=_f(13)),
    body=TextStyle(color="#D6EAF5", font=_f(14)),
    mono=TextStyle(color="#67E8F9", font=_f(14, 500, MONO)),
    button=ButtonStyle(
        background="#0891B2", backgroundHover="#0EA5C9", backgroundPressed="#0E7490",
        text="#FFFFFF", radius=10, font=_f(14, 600),
    ),
    buttonSecondary=ButtonStyle(
        background="#16304A", backgroundHover="#1C3B5A", backgroundPressed="#23476B",
        text="#D6EAF5", radius=10, font=_f(14, 500),
    ),
    table=TableStyle(
        headerBackground="#132B42", headerText="#7FA7C2", headerFont=_f(12, 700),
        rowBackground="#102233", rowAlternate="#12273A", rowHover="#173550",
        text="#D6EAF5", font=_f(13), border="#1B3550",
    ),
    input=InputStyle(
        background="#0D1D2C", border="#1F3D5C", borderFocus="#22D3EE",
        text="#E0F7FF", placeholder="#5B7F99", radius=10, font=_f(14),
    ),
    status=StatusColors(
        success="#34D399", invalid="#F87171", review="#FBBF24",
        error="#C4B5FD", pending="#5B7F99",
    ),
)

THEMES: dict[str, Theme] = {t.id: t for t in (CLARO, ESCURO, LARANJA_PRETO, OCEANO)}


def resolve_theme(theme_id: str, sistema_escuro: bool) -> Theme:
    """Resolve o id escolhido (inclusive 'system') para um tema concreto."""
    if theme_id == SYSTEM_ID or theme_id not in THEMES:
        return ESCURO if sistema_escuro else CLARO
    return THEMES[theme_id]
