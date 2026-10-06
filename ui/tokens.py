"""Design Tokens do InsurMinds — Insurance Intelligence v1.0.
Centraliza as definições visuais do produto: paleta corporativa, tipografia, espaçamento,
raios de borda, sombras e breakpoints responsivos.
"""
from dataclasses import dataclass
from typing import Dict, Any


# =============================================================================
# 1. PALETA CORPORATIVA — INSURANCE INTELLIGENCE
# =============================================================================
@dataclass(frozen=True)
class ColorTokens:
    PRIMARY_NAVY: str = "#12304A"      # Navegação, headings, autoridade institucional
    PRIMARY_BLUE: str = "#2864C7"      # Ações primárias, links ativos, destaques
    SECONDARY_TEAL: str = "#0B8A84"    # Informação, estado positivo, rastreabilidade
    SUCCESS: str = "#197B5C"           # Confirmado, equivalente, regularidade
    ATTENTION: str = "#F59E0B"         # Atenção, alteração moderada, aviso
    CRITICAL: str = "#D94A4A"          # Alteração crítica, divergência, exclusão
    BACKGROUND: str = "#F5F7FA"        # Canvas global institucional (fundo claro)
    SURFACE: str = "#FFFFFF"           # Cartões, painéis, modais
    BORDER: str = "#D9E1E8"            # Linhas divisórias, contornos sutis
    TEXT_MAIN: str = "#1F2A35"         # Texto principal de alta legibilidade
    TEXT_MUTED: str = "#6B7785"        # Texto secundário, legendas, metadados
    SURFACE_HOVER: str = "#F0F4F8"     # Hover em superfícies e itens de menu
    SURFACE_MUTED: str = "#F8FAFC"     # Fundo de snippets e blocos de evidência


COLORS = ColorTokens()


# =============================================================================
# 2. TIPOGRAFIA — INTER & IBM PLEX MONO
# =============================================================================
@dataclass(frozen=True)
class TypographyTokens:
    FONT_UI: str = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    FONT_CODE: str = "'IBM Plex Mono', 'Menlo', 'Consolas', monospace"

    # Escalas Tipográficas Oficiais (Tamanho / Line-Height / Peso)
    H1: str = "24px / 32px 600"
    H2: str = "20px / 28px 600"
    H3: str = "16px / 24px 600"
    BODY: str = "14px / 22px 400"
    BODY_SEMIBOLD: str = "14px / 22px 600"
    CAPTION: str = "12px / 18px 400"
    CAPTION_SEMIBOLD: str = "12px / 18px 600"
    CODE_SNIPPET: str = "12.5px / 20px 400"


TYPOGRAPHY = TypographyTokens()


# =============================================================================
# 3. ESPAÇAMENTO — ESCALA CORPORATIVA
# =============================================================================
@dataclass(frozen=True)
class SpacingTokens:
    MICRO: str = "4px"     # Ajustes finos, espaçamento entre ícone e texto
    COMPACT: str = "8px"   # Espaçamento interno de badges e botões compactos
    INTERNAL: str = "12px" # Padding interno de cards e campos
    STANDARD: str = "16px" # Espaçamento padrão entre elementos
    BLOCK: str = "24px"    # Separação entre blocos de conteúdo
    SECTION: str = "32px"  # Espaçamento entre seções principais
    LARGE: str = "48px"    # Grandes divisões de layout


SPACING = SpacingTokens()


# =============================================================================
# 4. RAIOS DE BORDA (BORDER RADIUS)
# =============================================================================
@dataclass(frozen=True)
class RadiusTokens:
    SM: str = "4px"        # Badges pequenos, tags técnicas
    MD: str = "8px"        # Botões, inputs, painéis secundários
    LG: str = "12px"       # Cartões de diferença, containers principais
    XL: str = "16px"       # Modais, hero panels
    PILL: str = "9999px"   # Status badges arredondados, pílulas de navegação


RADIUS = RadiusTokens()


# =============================================================================
# 5. SOMBRAS — PROFUNDIDADE SÓBRIA
# =============================================================================
@dataclass(frozen=True)
class ShadowTokens:
    NONE: str = "none"
    SM: str = "0 1px 3px rgba(18, 48, 74, 0.05), 0 1px 2px rgba(18, 48, 74, 0.03)"
    MD: str = "0 4px 6px -1px rgba(18, 48, 74, 0.07), 0 2px 4px -1px rgba(18, 48, 74, 0.04)"
    LG: str = "0 10px 15px -3px rgba(18, 48, 74, 0.08), 0 4px 6px -2px rgba(18, 48, 74, 0.03)"


SHADOWS = ShadowTokens()


# =============================================================================
# 6. BREAKPOINTS RESPONSIVOS
# =============================================================================
@dataclass(frozen=True)
class BreakpointTokens:
    DESKTOP_WIDE: str = "1440px" # Resolução primária prioritária
    NOTEBOOK: str = "1366px"     # Resolução padrão corporativa
    TABLET: str = "768px"        # 1 coluna assistida
    MOBILE: str = "480px"        # Fora do foco MVP, apenas proteção básica


BREAKPOINTS = BreakpointTokens()
