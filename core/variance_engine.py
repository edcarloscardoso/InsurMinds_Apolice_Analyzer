"""Motor analítico de cálculo de variância contábil de sinistros e detecção de maiores ofensores.
Aderente às normas da SUSEP (FIP / Quadro de Sinistros e Provisões Técnicas) e auditoria contábil.
"""
from typing import List, Dict, Any, Optional
from core.schemas import SinistroItem, RamoVarianceSummary, AuditoriaVarianceReport


# Dicionário canônico de Ramos SUSEP mais frequentes em seguros corporativos
RAMOS_SUSEP: Dict[str, str] = {
    "0378": "Responsabilidade Civil D&O (Administradores e Diretores)",
    "0351": "Responsabilidade Civil Geral (RCG)",
    "0171": "Patrimonial / Riscos Nomeados e Operacionais",
    "0531": "Automóvel Casco",
    "0746": "Seguro Garantia (Judicial e Performance)",
    "0118": "Habitacional em Apólices de Mercado",
    "0310": "Transportes Nacionais e Internacionais",
    "0993": "Vida em Grupo e Acidentes Pessoais"
}

# Tabela oficial de Tipos de Movimento SUSEP (FIP / Dados Operacionais)
TIPOS_MOVIMENTO_SUSEP: Dict[str, str] = {
    "101": "Emissão de Apólice",
    "102": "Endosso de cobrança adicional de prêmio",
    "103": "Endosso de restituição de prêmio",
    "104": "Cancelamento de Apólice com restituição de prêmio",
    "105": "Cancelamento de Endosso com restituição de prêmio",
    "106": "Cancelamento de Apólice sem restituição de prêmio",
    "107": "Cancelamento de Endosso sem restituição de prêmio",
    "108": "Endosso sem movimentação de prêmio"
}


def get_ramo_name(cod_ramo: Optional[str]) -> str:
    """Retorna a descrição oficial do ramo SUSEP com fallback amigável."""
    if not cod_ramo:
        return "Ramo Não Informado"
    cod = str(cod_ramo).strip().zfill(4)
    return RAMOS_SUSEP.get(cod, f"Ramo {cod}")


def get_tipo_mov_name(tipo_mov: Optional[str]) -> str:
    """Retorna a descrição oficial do Tipo de Movimento SUSEP."""
    if not tipo_mov:
        return "101 - Emissão de Apólice"
    cod = str(tipo_mov).strip()
    return f"{cod} - {TIPOS_MOVIMENTO_SUSEP.get(cod, 'Movimento Operacional')}"


def calculate_claims_variance(
    sinistros: List[SinistroItem],
    periodo_referencia: str = "08/2026"
) -> AuditoriaVarianceReport:
    """Calcula a variação contábil consolidada, agrupada por Ramo SUSEP, identificando os maiores ofensores.
    
    Atende aos requisitos de justificativa de variação para SUSEP e relatórios de auditoria externa.
    """
    if not sinistros:
        return AuditoriaVarianceReport(
            periodo_referencia=periodo_referencia,
            total_anterior_geral=0.0,
            total_atual_geral=0.0,
            delta_global=0.0,
            delta_global_percentual=0.0,
            justificativa_auditoria_markdown="*Nenhum registro de sinistro carregado para o período.*"
        )

    # 1. Totais Globais
    total_anterior_geral = sum(s.saldo_anterior for s in sinistros)
    total_atual_geral = sum(s.saldo_atual for s in sinistros)
    delta_global = total_atual_geral - total_anterior_geral
    delta_global_percentual = (
        (delta_global / total_anterior_geral * 100.0) if total_anterior_geral != 0 else 0.0
    )

    # 2. Agrupamento por Ramo SUSEP
    ramos_dict: Dict[str, Dict[str, Any]] = {}
    for s in sinistros:
        cod = str(s.cod_ramo).strip().zfill(4)
        if cod not in ramos_dict:
            ramos_dict[cod] = {
                "nome": s.ramo_nome or get_ramo_name(cod),
                "anterior": 0.0,
                "atual": 0.0,
                "qtd": 0
            }
        ramos_dict[cod]["anterior"] += s.saldo_anterior
        ramos_dict[cod]["atual"] += s.saldo_atual
        ramos_dict[cod]["qtd"] += 1

    # Soma absoluta das variações por ramo para ponderação do share
    soma_deltas_absolutos = sum(abs(v["atual"] - v["anterior"]) for v in ramos_dict.values()) or 1.0

    resumos_ramos: List[RamoVarianceSummary] = []
    for cod, dados in ramos_dict.items():
        delta_ramo = dados["atual"] - dados["anterior"]
        delta_pct = (delta_ramo / dados["anterior"] * 100.0) if dados["anterior"] != 0 else 0.0
        share = (abs(delta_ramo) / soma_deltas_absolutos) * 100.0

        resumos_ramos.append(RamoVarianceSummary(
            cod_ramo=cod,
            ramo_nome=dados["nome"],
            qtd_sinistros=dados["qtd"],
            total_anterior=round(dados["anterior"], 2),
            total_atual=round(dados["atual"], 2),
            delta_absoluto=round(delta_ramo, 2),
            delta_percentual=round(delta_pct, 2),
            share_na_variacao_total=round(share, 2),
            is_maior_ofensor=False
        ))

    # Ordena ramos pelo maior impacto absoluto na variação
    resumos_ramos.sort(key=lambda r: abs(r.delta_absoluto), reverse=True)
    if resumos_ramos:
        resumos_ramos[0].is_maior_ofensor = True
        ramo_maior_ofensor = resumos_ramos[0]
    else:
        ramo_maior_ofensor = None

    # 3. Identificação do Sinistro Individual Maior Ofensor
    sinistros_ordenados = sorted(sinistros, key=lambda s: abs(s.delta_variacao), reverse=True)
    sinistro_maior_ofensor = sinistros_ordenados[0] if sinistros_ordenados else None
    top_ofensores = sinistros_ordenados[:5]

    # 4. Geração da Justificativa Técnica Preliminar
    sinal = "+" if delta_global >= 0 else ""
    
    ramo_info = f"Ramo {ramo_maior_ofensor.cod_ramo} — {ramo_maior_ofensor.ramo_nome}" if ramo_maior_ofensor else "N/A"
    ramo_delta = f"{sinal}R$ {ramo_maior_ofensor.delta_absoluto:,.2f} ({sinal}{ramo_maior_ofensor.delta_percentual:.2f}%)" if ramo_maior_ofensor else "R$ 0,00"
    ramo_share = f"{ramo_maior_ofensor.share_na_variacao_total:.1f}%" if ramo_maior_ofensor else "0%"

    sinistro_info = f"Sinistro nº {sinistro_maior_ofensor.numero_sinistro} (Apólice nº `{sinistro_maior_ofensor.numero_apolice}`, Segurado: *{sinistro_maior_ofensor.segurado}*)" if sinistro_maior_ofensor else "N/A"
    sinistro_delta = f"{sinal}R$ {sinistro_maior_ofensor.delta_variacao:,.2f}" if sinistro_maior_ofensor else "R$ 0,00"
    sinistro_causa = sinistro_maior_ofensor.causa_sinistro if sinistro_maior_ofensor else "N/A"
    sinistro_status = sinistro_maior_ofensor.status_sinistro if sinistro_maior_ofensor else "N/A"
    sinistro_tipo = get_tipo_mov_name(sinistro_maior_ofensor.tipo_mov) if sinistro_maior_ofensor else "N/A"

    justificativa_md = f"""### 📌 Nota Explicativa de Variação de Provisão de Sinistros (SUSEP / Auditoria)
**Período de Referência:** {periodo_referencia}  
**Saldo Anterior:** R$ {total_anterior_geral:,.2f} | **Saldo Atualizado:** R$ {total_atual_geral:,.2f} | **Variação Líquida:** {sinal}R$ {delta_global:,.2f} ({sinal}{delta_global_percentual:.2f}%)

#### 1. Ramo Maior Ofensor
A variação global na provisão de sinistros no período foi explicada precipuamente pelo **{ramo_info}**, o qual apresentou uma oscilação líquida de **{ramo_delta}**, representando **{ramo_share} da variação total observada na carteira**.

#### 2. Apólice e Sinistro de Maior Impacto (Maior Ofensor da Carteira)
O evento com maior repercussão individual no fechamento contábil foi o **{sinistro_info}**, que sofreu um ajuste de provisão de **{sinistro_delta}**. 
* **Motivo/Causa:** {sinistro_causa}
* **Status Processual:** {sinistro_status}
* **Tipo de Movimento:** {sinistro_tipo}

Essa movimentação atende aos preceitos da Circular SUSEP de constituição de Provisões Técnicas e reflete a reavaliação tempestiva das reservas com base nos relatórios de regulação jurídica e pericial.
"""

    return AuditoriaVarianceReport(
        periodo_referencia=periodo_referencia,
        total_anterior_geral=round(total_anterior_geral, 2),
        total_atual_geral=round(total_atual_geral, 2),
        delta_global=round(delta_global, 2),
        delta_global_percentual=round(delta_global_percentual, 2),
        ramo_maior_ofensor=ramo_maior_ofensor,
        sinistro_maior_ofensor=sinistro_maior_ofensor,
        variacao_por_ramo=resumos_ramos,
        top_sinistros_ofensores=top_ofensores,
        justificativa_auditoria_markdown=justificativa_md
    )


def generate_sample_accounting_data() -> List[SinistroItem]:
    """Gera base simulada realista de fechamento contábil mensal (PSL / FIP SUSEP)."""
    return [
        SinistroItem(
            numero_sinistro="SIN-2026-0378-01",
            numero_apolice="01.0775.000458/01",
            segurado="TechCorp Brasil Inovações S.A.",
            seguradora="Allianz Global Corporate & Specialty",
            cod_ramo="0378",
            ramo_nome="Responsabilidade Civil D&O",
            tipo_mov="101",
            saldo_anterior=1200000.00,
            saldo_atual=4800000.00,
            delta_variacao=3600000.00,
            delta_percentual=300.00,
            status_sinistro="Sob Regulação",
            causa_sinistro="Reclamação arbitral instaurada por minoritários envolvendo alegação de falha de disclosure em rodada de captação (Side A/B)."
        ),
        SinistroItem(
            numero_sinistro="SIN-2026-0378-02",
            numero_apolice="02.0889.001924/02",
            segurado="InovaLogística Distribuição S.A.",
            seguradora="Chubb Seguros Brasil",
            cod_ramo="0378",
            ramo_nome="Responsabilidade Civil D&O",
            tipo_mov="101",
            saldo_anterior=450000.00,
            saldo_atual=950000.00,
            delta_variacao=500000.00,
            delta_percentual=111.11,
            status_sinistro="Avisado",
            causa_sinistro="Instauração de processo administrativo sancionador pela CVM com adiantamento emergencial de custos de defesa."
        ),
        SinistroItem(
            numero_sinistro="SIN-2026-0351-01",
            numero_apolice="05.0351.002281/00",
            segurado="Metalúrgica Gerdau & Filhos Ltda.",
            seguradora="Porto Seguro Cia de Seguros",
            cod_ramo="0351",
            ramo_nome="Responsabilidade Civil Geral (RCG)",
            tipo_mov="101",
            saldo_anterior=850000.00,
            saldo_atual=1100000.00,
            delta_variacao=250000.00,
            delta_percentual=29.41,
            status_sinistro="Sob Regulação",
            causa_sinistro="Incidente de danos materiais a terceiros durante operação de guindaste em canteiro industrial."
        ),
        SinistroItem(
            numero_sinistro="SIN-2026-0171-01",
            numero_apolice="08.0171.000943/01",
            segurado="Rede Varejista SuperMax S.A.",
            seguradora="Bradesco Auto/RE Companhia de Seguros",
            cod_ramo="0171",
            ramo_nome="Patrimonial / Riscos Operacionais",
            tipo_mov="102",
            saldo_anterior=2100000.00,
            saldo_atual=1950000.00,
            delta_variacao=-150000.00,
            delta_percentual=-7.14,
            status_sinistro="Liquidado",
            causa_sinistro="Sinistro de vendaval parcialmente liquidado após apuração final de salvados e franquia contratual."
        ),
        SinistroItem(
            numero_sinistro="SIN-2026-0531-01",
            numero_apolice="12.0531.004112/03",
            segurado="Transportes Rápidos Paulista Eireli",
            seguradora="Tokio Marine Seguradora S.A.",
            cod_ramo="0531",
            ramo_nome="Automóvel Casco",
            tipo_mov="101",
            saldo_anterior=320000.00,
            saldo_atual=390000.00,
            delta_variacao=70000.00,
            delta_percentual=21.88,
            status_sinistro="Avisado",
            causa_sinistro="Colisão múltipla de frota comercial em rodovia com perda parcial."
        ),
        SinistroItem(
            numero_sinistro="SIN-2026-0746-01",
            numero_apolice="15.0746.000122/00",
            segurado="Construtora Horizonte Norte S.A.",
            seguradora="Junto Seguros S.A.",
            cod_ramo="0746",
            ramo_nome="Seguro Garantia (Judicial)",
            tipo_mov="108",
            saldo_anterior=1500000.00,
            saldo_atual=1500000.00,
            delta_variacao=0.00,
            delta_percentual=0.00,
            status_sinistro="Judicializado",
            causa_sinistro="Garantia recursal com suspensão de exigibilidade sem alteração na expectativa de perda."
        )
    ]
