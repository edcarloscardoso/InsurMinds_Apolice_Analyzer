"""Gerador de apólices sintéticas de seguro D&O realistas em PDF para demonstração e testes.
Utiliza a biblioteca ReportLab para compilar documentos de padrão corporativo fiel às normas da SUSEP.
"""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def create_policy_pdf(
    output_path: Path,
    seguradora: str,
    segurado: str,
    num_apolice: str,
    vigencia: str,
    premio: str,
    lmg: str,
    franquia: str,
    retroatividade: str,
    territorio: str,
    coberturas: list[str],
    exclusoes: list[str],
    clausulas_especiais: list[str]
):
    """Gera um documento PDF profissional de apólice de seguro D&O."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#0f2b48")
    accent_color = colors.HexColor("#1b6ca8")
    light_bg = colors.HexColor("#f4f7fa")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        textColor=accent_color,
        spaceAfter=12
    )

    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=13,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#2d3748")
    )

    story = []

    # Cabeçalho da Apólice
    story.append(Paragraph(f"<b>{seguradora.upper()}</b>", title_style))
    story.append(Paragraph("APÓLICE DE SEGURO DE RESPONSABILIDADE CIVIL DE DIRETORES E ADMINISTRADORES (D&O)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=accent_color, spaceAfter=12))

    # Tabela de Dados Gerais
    dados_gerais = [
        [Paragraph("<b>Tomador / Segurado:</b>", body_style), Paragraph(segurado, body_style)],
        [Paragraph("<b>Apólice Nº:</b>", body_style), Paragraph(num_apolice, body_style)],
        [Paragraph("<b>Período de Vigência:</b>", body_style), Paragraph(vigencia, body_style)],
        [Paragraph("<b>Limite Máximo de Garantia (LMG):</b>", body_style), Paragraph(f"<b>{lmg}</b>", body_style)],
        [Paragraph("<b>Franquia / Retenção:</b>", body_style), Paragraph(franquia, body_style)],
        [Paragraph("<b>Prêmio Total:</b>", body_style), Paragraph(premio, body_style)],
        [Paragraph("<b>Data de Retroatividade:</b>", body_style), Paragraph(retroatividade, body_style)],
        [Paragraph("<b>Âmbito Territorial:</b>", body_style), Paragraph(territorio, body_style)],
        [Paragraph("<b>Legislação e Foro:</b>", body_style), Paragraph("Legislação Brasileira, Foro da Comarca de São Paulo/SP", body_style)]
    ]

    t_gerais = Table(dados_gerais, colWidths=[180, 340])
    t_gerais.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), light_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t_gerais)
    story.append(Spacer(1, 14))

    # Seção de Coberturas
    story.append(Paragraph("1. QUADRO DE COBERTURAS CONTRATADAS", heading_style))
    story.append(Paragraph("A presente apólice garante, até o Limite Máximo de Garantia estipulado, as seguintes coberturas:", body_style))
    story.append(Spacer(1, 4))
    
    for cob in coberturas:
        story.append(Paragraph(f"• <b>{cob}</b>", body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 12))

    # Seção de Exclusões
    story.append(Paragraph("2. RISCOS EXPRESSAMENTE EXCLUÍDOS", heading_style))
    story.append(Paragraph("Não estão cobertas por este contrato de seguro reclamações fundadas em:", body_style))
    story.append(Spacer(1, 4))

    for exc in exclusoes:
        story.append(Paragraph(f"• {exc}", body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 12))

    # Cláusulas Especiais e Endossos
    story.append(Paragraph("3. CLÁUSULAS PARTICULARES E ENDOSSOS", heading_style))
    for cl in clausulas_especiais:
        story.append(Paragraph(f"• {cl}", body_style))
        story.append(Spacer(1, 2))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=8))
    story.append(Paragraph("<i>Documento emitido em conformidade com as Circulares SUSEP vigentes. Registro da Apólice no Sistema Nacional de Seguros.</i>", body_style))

    doc.build(story)
    print(f"✅ Apólice gerada com sucesso: {output_path}")


def generate_all_samples():
    """Gera o conjunto completo de apólices sintéticas para demonstração."""
    base_dir = Path(__file__).resolve().parent / "sample_policies"
    base_dir.mkdir(parents=True, exist_ok=True)

    # 1. Allianz D&O
    create_policy_pdf(
        output_path=base_dir / "apolice_do_allianz.pdf",
        seguradora="Allianz Global Corporate & Specialty Resseguros Brasil S.A.",
        segurado="TechCorp Brasil Inovações e Soluções Tecnológicas S.A.",
        num_apolice="01.0775.000458/01",
        vigencia="01/01/2026 a 01/01/2027",
        premio="R$ 120.000,00",
        lmg="R$ 10.000.000,00",
        franquia="R$ 50.000,00 (Isento para Cobertura Side A)",
        retroatividade="01/01/2023 (3 anos de retroatividade)",
        territorio="Brasil e Jurisdição Mundial (exceto EUA e Canadá)",
        coberturas=[
            "Cobertura Side A (Indivíduos não indenizados pela sociedade)",
            "Cobertura Side B (Reembolso da Sociedade)",
            "Cobertura Side C (Sociedade por ações em reclamações de valores mobiliários)",
            "Custos de Defesa e Honorários Advocatícios Antecipados",
            "Custos de Investigação Regulatória (CVM, BACEN, CADE)",
            "Extensão de Cobertura para Penhora Online e Bloqueio de Bens",
            "Despesas de Publicidade e Gestão de Crise de Imagem",
            "Multas e Penalidades Civis Seguráveis",
            "Prazo Complementar de Notificação (24 meses)"
        ],
        exclusoes=[
            "Atos dolosos, fraude comprovada ou conduta criminal transitada em julgado",
            "Obtenção de lucro ou vantagem financeira indevida",
            "Danos corporais, morte e danos materiais diretos",
            "Poluição e contaminação ambiental (salvo custos de defesa emergenciais)",
            "Reclamações anteriores ou fatos conhecidos antes da data de retroatividade",
            "Litígios societários entre segurados (Insured vs. Insured)"
        ],
        clausulas_especiais=[
            "Cláusula de Não Imputação Mútua de Dolo",
            "Cláusula de Adiantamento Automático de Custos de Defesa em até 15 dias úteis",
            "Extensão de Cobertura para Cônjuges e Herdeiros"
        ]
    )

    # 2. Chubb D&O
    create_policy_pdf(
        output_path=base_dir / "apolice_do_chubb.pdf",
        seguradora="Chubb Seguros Brasil S.A.",
        segurado="TechCorp Brasil Inovações e Soluções Tecnológicas S.A.",
        num_apolice="02.0889.001924/02",
        vigencia="01/01/2026 a 01/01/2027",
        premio="R$ 85.000,00",
        lmg="R$ 5.000.000,00",
        franquia="R$ 100.000,00",
        retroatividade="01/01/2021 (5 anos de retroatividade)",
        territorio="Brasil e Jurisdição Mundial (exceto EUA e Canadá)",
        coberturas=[
            "Cobertura Side A (Indivíduos não indenizados pela sociedade)",
            "Cobertura Side B (Reembolso da Sociedade)",
            "Cobertura Side A DIC (Difference in Conditions / Excesso)",
            "Custos de Defesa e Honorários Advocatícios Antecipados",
            "Cobertura para Danos Ambientais - Custos de Defesa Limitados",
            "Cobertura Automática para Novas Subsidiárias (até 25% de ativos)",
            "Prazo Complementar de Notificação (36 meses)"
        ],
        exclusoes=[
            "Atos dolosos, fraude comprovada ou conduta criminal transitada em julgado",
            "Obtenção de lucro ou vantagem financeira indevida",
            "Danos corporais, morte e danos materiais diretos",
            "Reclamações anteriores ou fatos conhecidos antes da data de retroatividade",
            "Litígios societários entre segurados (Insured vs. Insured)",
            "Violação de leis de valores mobiliários norte-americanas (SEC / Rule 10b-5)"
        ],
        clausulas_especiais=[
            "Cláusula de Bilateralidade no Cancelamento",
            "Extensão para Ex-Administradores e Aposentados por até 72 meses",
            "Proteção Patrimonial de Bens Penhorados em Execuções Trabalhistas"
        ]
    )

    # 3. AIG D&O
    create_policy_pdf(
        output_path=base_dir / "apolice_do_aig.pdf",
        seguradora="AIG Seguros Brasil S.A.",
        segurado="TechCorp Brasil Inovações e Soluções Tecnológicas S.A.",
        num_apolice="03.0991.003411/00",
        vigencia="01/01/2026 a 01/01/2027",
        premio="R$ 160.000,00",
        lmg="R$ 15.000.000,00",
        franquia="R$ 75.000,00",
        retroatividade="Ilimitada (exceto fatos prévios e conhecidos)",
        territorio="Mundial (inclusive EUA e Canadá)",
        coberturas=[
            "Cobertura Side A (Indivíduos não indenizados pela sociedade)",
            "Cobertura Side B (Reembolso da Sociedade)",
            "Cobertura Side C (Sociedade por ações em reclamações de valores mobiliários)",
            "Custos de Defesa e Honorários Advocatícios Antecipados",
            "Custos de Investigação Regulatória (CVM, BACEN, CADE, SEC, DOJ)",
            "Extensão de Cobertura para Penhora Online e Bloqueio de Bens",
            "Despesas de Publicidade e Gestão de Crise de Imagem",
            "Extraterritorialidade EUA e Canadá (Litígios Transfronteiriços)",
            "Prazo Complementar de Notificação (36 meses)"
        ],
        exclusoes=[
            "Atos dolosos, fraude comprovada ou conduta criminal transitada em julgado",
            "Obtenção de lucro ou vantagem financeira indevida",
            "Danos corporais, morte e danos materiais diretos",
            "Poluição e contaminação ambiental (salvo custos de defesa emergenciais)",
            "Reclamações anteriores ou fatos conhecidos antes da data de retroatividade"
        ],
        clausulas_especiais=[
            "Garantia de Manutenção de Defesa em Casos de Insolvência da Empresa",
            "Cláusula de Severabilidade de Conduta entre Segurados",
            "Indenização por Danos Morais Decorrentes de Gestão Corporativa"
        ]
    )


if __name__ == "__main__":
    generate_all_samples()
