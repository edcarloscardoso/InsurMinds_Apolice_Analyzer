"""Esquemas de dados canônicos e contratos de interface do InsurMinds Apólice Analyzer.
Utiliza Pydantic v2 para validação estrita, coerção e integridade de tipos.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ApoliceDAO(BaseModel):
    """Objeto de Transferência de Dados Canônico que representa uma apólice D&O estruturada."""

    # Identificação & Rastreabilidade
    id: Optional[str] = Field(default=None, description="Hash MD5 do arquivo original (Chave Primária)")
    nome_arquivo: str = Field(..., description="Nome original do documento PDF")
    data_processamento: str = Field(..., description="Data/hora ISO do processamento")

    # Metadados Contratuais
    numero_apolice: Optional[str] = Field(default=None, description="Número de registro da apólice na SUSEP / seguradora")
    segurado: Optional[str] = Field(default=None, description="Razão social da empresa segurada (Tomador)")
    seguradora: Optional[str] = Field(default=None, description="Nome da companhia seguradora emissora")
    vigencia_inicio: Optional[str] = Field(default=None, description="Data de início da vigência (ex: DD/MM/AAAA)")
    vigencia_fim: Optional[str] = Field(default=None, description="Data de término da vigência (ex: DD/MM/AAAA)")

    # Parâmetros Financeiros
    premio_total: Optional[str] = Field(default=None, description="Prêmio total contratado formatado")
    limite_responsabilidade: Optional[str] = Field(default=None, description="Limite Máximo de Garantia (LMG) / Limite Agregado")
    franquia: Optional[str] = Field(default=None, description="Franquia (Retention/Deductible) aplicável")

    # Coberturas e Exclusões (D&O Side A/B/C e extensões)
    coberturas: List[str] = Field(default_factory=list, description="Lista de coberturas básicas e adicionais contratadas")
    exclusoes: List[str] = Field(default_factory=list, description="Lista de riscos expressamente excluídos")
    clausulas_especiais: List[str] = Field(default_factory=list, description="Cláusulas particulares, endossos ou aditivos")

    # Escopo Territorial e Temporal
    retroatividade: Optional[str] = Field(default=None, description="Data ou prazo de retroatividade da cobertura")
    territorio: Optional[str] = Field(default=None, description="Abrangência territorial e jurisdicional")
    legislacao_aplicavel: Optional[str] = Field(default=None, description="Legislação, jurisdição e foro")

    # Auditoria de Extração
    metodo_extracao: str = Field(default="pdfplumber", description="'pdfplumber' | 'gemini_vision' | 'mock_fallback'")
    confianca_extracao: float = Field(default=1.0, ge=0.0, le=1.0, description="Nível de confiança da extração (0.0 a 1.0)")
    campos_nao_encontrados: List[str] = Field(default_factory=list, description="Lista de campos que não puderam ser extraídos")


class FieldDiff(BaseModel):
    """Representa a divergência ou convergência em um campo específico entre duas apólices."""
    campo: str = Field(..., description="Nome do campo analisado")
    rotulo: str = Field(..., description="Nome legível para exibição ao usuário")
    valor_apolice_a: Optional[str] = Field(default=None, description="Valor contido na apólice A")
    valor_apolice_b: Optional[str] = Field(default=None, description="Valor contido na apólice B")
    ha_diferenca: bool = Field(..., description="True se houver discrepância entre os valores")
    tipo_diferenca: str = Field(
        ...,
        description="'igual' | 'valor' | 'ausente_a' | 'ausente_b' | 'ambos_ausentes'"
    )


class ComparisonResult(BaseModel):
    """Resultado consolidado da comparação entre duas apólices estruturadas."""
    apolice_a_id: str = Field(..., description="ID da Apólice A")
    apolice_b_id: str = Field(..., description="ID da Apólice B")
    apolice_a_nome: str = Field(..., description="Nome/Seguradora da Apólice A")
    apolice_b_nome: str = Field(..., description="Nome/Seguradora da Apólice B")
    data_comparacao: str = Field(..., description="Data/hora ISO da comparação")
    score_similaridade: float = Field(..., ge=0.0, le=100.0, description="Score percentual de similaridade (0 a 100)")
    diffs: List[FieldDiff] = Field(default_factory=list, description="Lista detalhada de comparações campo a campo")
    
    # Análise de Conjuntos de Coberturas
    coberturas_exclusivas_a: List[str] = Field(default_factory=list, description="Coberturas presentes apenas na apólice A")
    coberturas_exclusivas_b: List[str] = Field(default_factory=list, description="Coberturas presentes apenas na apólice B")
    coberturas_comuns: List[str] = Field(default_factory=list, description="Coberturas equivalentes presentes em ambas")

    # Análise de Conjuntos de Exclusões
    exclusoes_exclusivas_a: List[str] = Field(default_factory=list, description="Exclusões presentes apenas na apólice A")
    exclusoes_exclusivas_b: List[str] = Field(default_factory=list, description="Exclusões presentes apenas na apólice B")
    exclusoes_comuns: List[str] = Field(default_factory=list, description="Exclusões equivalentes presentes em ambas")


class DocumentState(BaseModel):
    """Estado transportado através do grafo de agentes durante a ingestão de um documento."""
    file_path: str = ""
    file_name: str = ""
    file_size: int = 0
    file_hash: str = ""
    page_count: int = 0
    raw_text: str = ""
    is_scanned: bool = False
    extraction_method: str = "pdfplumber"
    identified_sections: Dict[str, str] = Field(default_factory=dict)
    structured_data: Optional[ApoliceDAO] = None
    status: str = "iniciado"
    errors: List[str] = Field(default_factory=list)


class ComparisonState(BaseModel):
    """Estado transportado através do grafo durante a comparação e geração de relatório."""
    apolice_a: Optional[ApoliceDAO] = None
    apolice_b: Optional[ApoliceDAO] = None
    diff_result: Optional[ComparisonResult] = None
    report_markdown: str = ""
    status: str = "iniciado"
    errors: List[str] = Field(default_factory=list)
