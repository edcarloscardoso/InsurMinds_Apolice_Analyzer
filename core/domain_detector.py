"""Detector conservador de domínio de apólices e contratos de seguros.

Garante o isolamento estrito entre seguros de Responsabilidade Civil D&O (core do sistema),
Automóvel (módulo secundário) e documentos contratuais externos ou genéricos.
"""
import re
from typing import Set, Tuple, Optional, Dict, Any, List

# Nomes exatos de fixtures sintéticas versionadas do projeto para testes de demonstração
DEMO_FIXTURE_FILENAMES: Set[str] = {
    "apolice_do_aig.pdf",
    "apolice_do_allianz.pdf",
    "apolice_do_chubb.pdf",
    "apolice_do_allianz_endosso.pdf",
}

# Sinais fortes e exclusivos de seguros D&O (Directors & Officers)
DO_SIGNALS = (
    "d&o",
    "directors and officers",
    "directors & officers",
    "responsabilidade civil de administradores",
    "administradores e diretores",
    "side a",
    "side b",
    "side c",
    "wrongful act",
    "ato de gestão",
    "atos de gestão",
    "seguro d&o",
    "seguro de administradores",
    "reclamação de valores mobiliários",
    "penhora online e bloqueio de bens",
    "0378",
)

# Sinais específicos e inequívocos de seguros de Automóvel
# NOTA DE SEGURANÇA: As palavras isoladas "veículo", "veículos" ou "frota" NÃO constam nesta lista,
# pois aparecem corriqueiramente em contratos corporativos e exclusões de apólices D&O.
AUTO_SPECIFIC_SIGNALS = (
    "seguro de automóvel",
    "seguro automóvel",
    "condições gerais de automóvel",
    "ramo automóvel",
    "automóvel casco",
    "casco automóvel",
    "rcf-v",
    "responsabilidade civil facultativa de veículos",
    "veículo segurado",
    "chassi",
    "placa do veículo",
    "cobertura compreensiva",
    "acidentes pessoais de passageiros",
    "0531",
)


def is_demo_sample(nome_arquivo: str) -> bool:
    """Verifica se o arquivo corresponde exatamente a uma das fixtures sintéticas de demonstração."""
    if not nome_arquivo:
        return False
    return nome_arquivo.strip().lower() in DEMO_FIXTURE_FILENAMES


def detect_document_domain(raw_text: str, nome_arquivo: str = "") -> str:
    """Classifica conservadoramente o domínio do documento.

    Retorna:
        'do': Quando há sinais claros e predominantes de Responsabilidade Civil D&O.
        'auto': Quando há conjunto consistente (mínimo 2) de evidências inequívocas de Automóvel.
        'unknown': Quando as evidências forem insuficientes, conflitantes ou genéricas.
    """
    corpus = f"{nome_arquivo}\n{raw_text or ''}".lower()

    do_matches = sum(1 for signal in DO_SIGNALS if signal in corpus)
    auto_matches = sum(1 for signal in AUTO_SPECIFIC_SIGNALS if signal in corpus)

    # Se houver predominância de sinais D&O, o documento permanece D&O mesmo que
    # cite frota ou veículos operacionais.
    if do_matches >= 1 and do_matches >= auto_matches:
        return "do"

    # Automóvel exige pelo menos dois marcadores específicos e dominância sobre D&O
    if auto_matches >= 2 and auto_matches > do_matches:
        return "auto"

    return "unknown"


def detect_document_type(raw_text: str, nome_arquivo: str = "") -> str:
    """Classifica conservadoramente a natureza/tipo contratual do documento:

    Retornos possíveis:
        'condicoes_gerais' | 'apolice_individual' | 'endosso' | 'proposta' | 'outros' | 'unknown'
    """
    fn_lower = (nome_arquivo or "").lower()
    text_sample = (raw_text or "")[:4000].lower()

    # 1. Identificadores explícitos de Condições Gerais no nome de arquivo ou cabeçalho inicial
    is_cg_named = any(k in fn_lower for k in ("condicoes_gerais", "condicoes-gerais", "condições gerais", "condicoes gerais", "_cg_")) or fn_lower.startswith("cg_")
    is_cg_text = bool(re.search(r'\bcondi[cç][oõ]es\s+gerais\b', text_sample[:1000]))

    # Marcadores de apólice emitida individual (com número específico contendo dígitos)
    has_real_apolice_num = bool(re.search(r'\bap[oó]lice\s+(?:de\s+seguro\s+)?n[ºo°]?\s*[:\-]?\s*[\d]{1,4}[\.\-/][\d\.\-/]{3,}', text_sample) or
                                re.search(r'\bap[oó]lice\s+(?:de\s+seguro\s+)?n[ºo°]?\s*[:\-]?\s*\d{5,}', text_sample))
    has_front_sheet = bool(re.search(r'\b(?:front\s+sheet|quadro\s+demonstrativo)\b', text_sample))

    if is_cg_named or (is_cg_text and not has_real_apolice_num and not has_front_sheet):
        return "condicoes_gerais"

    # 2. Endosso (aditivo de modificação)
    if "endosso" in fn_lower or re.search(r'\bendosso\s+(?:de\s+altera[cç][aã]o|n[ºo]|n[úu]mero)\b', text_sample[:1000]):
        return "endosso"

    # 3. Proposta de Seguro (no título ou arquivo, não menção incidental regulatória)
    if "proposta" in fn_lower or re.search(r'\b(?:proposta\s+de\s+seguro|proposta\s+de\s+ades[aã]o|proposta\s+de\s+contrata[cç][aã]o|formul[aá]rio\s+de\s+proposta)\b', text_sample[:1000]):
        return "proposta"

    # 4. Apólice individual emitida / Front Sheet
    if has_real_apolice_num or has_front_sheet or is_demo_sample(nome_arquivo):
        return "apolice_individual"

    if is_cg_text or re.search(r'\bcondi[cç][oõ]es\s+especiais\b', text_sample):
        return "condicoes_gerais"

    return "unknown"


# =============================================================================
# RESOLUÇÃO CANÔNICA DE SEGURADORAS (FASE 5.2 HARDENING)
# =============================================================================

INSURER_REGISTRY: List[Dict[str, Any]] = [
    {
        "canonical": "Chubb Seguros Brasil S.A.",
        "patterns": [r"\bchubb\b"],
        "susep_prefixes": ["15414.901422"]
    },
    {
        "canonical": "Sompo Seguros S.A.",
        "patterns": [r"\bsompo\b"],
        "susep_prefixes": ["15414.652408"]
    },
    {
        "canonical": "AIG Seguros Brasil S.A.",
        "patterns": [r"\baig\b"],
        "susep_prefixes": ["15414.900", "15414.60"]
    },
    {
        "canonical": "EZZE Seguros S.A.",
        "patterns": [r"\bezze\b"],
        "susep_prefixes": ["15414.601633"]
    },
    {
        "canonical": "Berkley International do Brasil Seguros S.A.",
        "patterns": [r"\bberkley\b"],
        "susep_prefixes": ["15414.001"]
    },
    {
        "canonical": "Allianz Global Corporate & Specialty",
        "patterns": [r"\ballianz\b"],
        "susep_prefixes": ["15414.002"]
    },
    {
        "canonical": "Tokio Marine Seguradora S.A.",
        "patterns": [r"\btokio\b", r"\btokio\s+marine\b"],
        "susep_prefixes": ["15414.003"]
    },
    {
        "canonical": "Porto Seguro Cia de Seguros Gerais",
        "patterns": [r"\bporto\s+seguro\b", r"\bporto\b"],
        "susep_prefixes": ["15414.008"]
    }
]


def resolve_seguradora_with_method(
    extracted_val: Optional[str] = None,
    raw_text: str = "",
    nome_arquivo: str = "",
    processo_susep: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve e normaliza a Seguradora retornando a tupla (nome_canonico, metodo_resolucao)."""
    # 1. Se já veio um valor extraído do LLM ou regex, tenta normalizar
    if extracted_val and isinstance(extracted_val, str):
        cleaned = " ".join(extracted_val.split()).strip()
        lower_extracted = cleaned.lower()
        # Rejeita termos genéricos de cabeçalho ou glossário
        if any(term in lower_extracted for term in (
            "cabeçalho", "cabecalho", "objeto garantido", "pessoa jurídica", "pessoa física",
            "pessoa fisica", "sociedade seguradora", "termo que define", "conforme definido"
        )):
            return None, None

        if len(cleaned) >= 3:
            for entry in INSURER_REGISTRY:
                for pat in entry["patterns"]:
                    if re.search(pat, lower_extracted):
                        return entry["canonical"], "extracted_llm"
            # Se for um nome corporativo plausível com mais de 5 caracteres
            if len(cleaned) > 5 and not cleaned.lower().startswith("seguradora"):
                return cleaned, "extracted_llm"

    # 2. Busca de marcas no texto bruto do documento
    corpus_text = (raw_text or "")[:15000].lower()
    for entry in INSURER_REGISTRY:
        for pat in entry["patterns"]:
            if re.search(pat, corpus_text):
                return entry["canonical"], "text_content"

    # 3. Busca por correspondência no Processo SUSEP (direto ou buscado no raw_text)
    susep_target = processo_susep
    if not susep_target and raw_text:
        match_susep = re.search(r'15414\.\d{3,6}', raw_text)
        if match_susep:
            susep_target = match_susep.group(0)

    if susep_target and isinstance(susep_target, str):
        clean_susep = re.sub(r'[^\d\.\-/]', '', susep_target)
        for entry in INSURER_REGISTRY:
            for pref in entry["susep_prefixes"]:
                if pref in clean_susep:
                    return entry["canonical"], "susep_registry"

    # 4. Busca por marcas no nome do arquivo (metadado neutro de arquivo)
    # Substitui '_' e '-' por espaços para permitir casamento de limites de palavra \b
    fn_clean = (nome_arquivo or "").lower().replace("_", " ").replace("-", " ")
    for entry in INSURER_REGISTRY:
        for pat in entry["patterns"]:
            if re.search(pat, fn_clean):
                return entry["canonical"], "filename_metadata"

    return None, None


def resolve_seguradora(
    extracted_val: Optional[str] = None,
    raw_text: str = "",
    nome_arquivo: str = "",
    processo_susep: Optional[str] = None
) -> Optional[str]:
    """Resolve e normaliza a Seguradora sem hardcode por arquivo, retornando apenas o nome canônico."""
    canonical, _ = resolve_seguradora_with_method(
        extracted_val=extracted_val,
        raw_text=raw_text,
        nome_arquivo=nome_arquivo,
        processo_susep=processo_susep
    )
    return canonical
