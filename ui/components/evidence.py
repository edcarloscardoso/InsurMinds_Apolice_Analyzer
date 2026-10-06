"""Componentes de Evidência Auditável do InsurMinds — Insurance Intelligence v1.0.
Consome estritamente o objeto EvidenceItem existente do backend (core.schemas.EvidenceItem).
Apresenta trechos contratuais literais em IBM Plex Mono com rastreabilidade de página e método.
"""
from typing import Optional, Dict, Any
import streamlit as st
from core.schemas import EvidenceItem
from ui.tokens import COLORS
from ui.styles import render_html


def render_evidence_snippet_html(
    snippet: Optional[str],
    page: Optional[int],
    method: Optional[str] = None,
    document_label: str = "Documento",
    doc_name: Optional[str] = None
) -> str:
    missing_msg = "Evidência documental não disponível para este item."
    text_content = snippet if (snippet and snippet.strip()) else missing_msg
    is_missing = text_content == missing_msg

    missing_style = "font-style: italic; color: #94A3B8;" if is_missing else "color: #1F2A35;"
    page_info = f" · <span class='evidence-page'>Pág. {page}</span>" if (page and not is_missing) else ""
    method_info = f"<span class='evidence-method'>Método: {method}</span>" if (method and not is_missing) else ""
    doc_header = f"{document_label}" + (f" ({doc_name})" if doc_name else "")

    return f"""
    <div class="im-evidence-snippet">
        <div class="im-evidence-header">
            <span class="im-evidence-source">📄 <b>{doc_header}</b>{page_info}</span>
            {method_info}
        </div>
        <div class="im-evidence-content" style="{missing_style}">
            "{text_content}"
        </div>
    </div>
    """


def render_evidence_panel(
    item_title: str,
    evidence_a: Optional[EvidenceItem] = None,
    evidence_b: Optional[EvidenceItem] = None,
    doc_a_name: str = "Documento A",
    doc_b_name: str = "Documento B",
    raw_text_a: Optional[str] = None,
    raw_text_b: Optional[str] = None,
    page_a: Optional[int] = None,
    page_b: Optional[int] = None
) -> None:
    """Renderiza um painel comparativo de evidências lado a lado consumindo EvidenceItem."""
    snippet_a = evidence_a.snippet if evidence_a else raw_text_a
    page_a_val = evidence_a.page if (evidence_a and evidence_a.page) else page_a
    method_a = evidence_a.method if evidence_a else None

    snippet_b = evidence_b.snippet if evidence_b else raw_text_b
    page_b_val = evidence_b.page if (evidence_b and evidence_b.page) else page_b
    method_b = evidence_b.method if evidence_b else None

    render_html(f"""
        <div class="im-evidence-panel">
            <div class="im-evidence-panel-title">
                🔍 <b>Evidência Contratual Auditável:</b> {item_title}
            </div>
            <div class="im-evidence-grid">
                <div>
                    {render_evidence_snippet_html(
                        snippet=snippet_a,
                        page=page_a_val,
                        method=method_a,
                        document_label="Documento A",
                        doc_name=doc_a_name
                    )}
                </div>
                <div>
                    {render_evidence_snippet_html(
                        snippet=snippet_b,
                        page=page_b_val,
                        method=method_b,
                        document_label="Documento B",
                        doc_name=doc_b_name
                    )}
                </div>
            </div>
        </div>
    """)
