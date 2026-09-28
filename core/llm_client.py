"""Cliente de integração com os modelos de IA Generativa (Google Gemini 2.0 Flash).
Fornece extração estruturada de cláusulas, fallback multimodal (Vision) e síntese de relatórios executivos.
Inclui provedor de contingência heurístico para execução contínua em modo offline ou demonstração.
"""
import os
import json
import logging
import re
from typing import Optional, Dict, Any, List
from core.config import GOOGLE_API_KEY, GEMINI_MODEL
from core.schemas import ApoliceDAO, ComparisonResult

logger = logging.getLogger(__name__)


class GeminiClient:
    """Cliente wrapper para o Google Gemini com suporte a fallback resiliente."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", "")
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Inicializa o SDK google-genai se a chave estiver configurada."""
        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key.strip())
                logger.info("Cliente Google GenAI conectado com sucesso.")
            except Exception as e:
                logger.warning(f"Não foi possível inicializar SDK google.genai: {e}. Usando contingência.")
                self.client = None
        else:
            logger.info("Nenhuma chave GOOGLE_API_KEY configurada. Operando em modo contingência / offline.")
            self.client = None

    def is_available(self) -> bool:
        """Indica se a API remota do Gemini está pronta para chamadas."""
        return self.client is not None

    @staticmethod
    def _is_demo_sample(nome_arquivo: str) -> bool:
        """Identifica exclusivamente fixtures sintéticas versionadas do projeto.
        
        O fallback de demonstração nunca deve ser aplicado por semelhança textual a
        documentos externos. Isso evita vazamento de dados sintéticos para documentos reais.
        """
        return nome_arquivo.lower() in {
            "apolice_do_aig.pdf",
            "apolice_do_allianz.pdf",
            "apolice_do_chubb.pdf",
            "apolice_do_allianz_endosso.pdf",
        }

    @staticmethod
    def _detect_document_domain(raw_text: str, nome_arquivo: str) -> str:
        """Classificação conservadora de domínio para o fallback offline.
        
        Retorna apenas 'do', 'auto' ou 'unknown'. A palavra isolada 'veículo' nunca
        é suficiente para classificar um documento como Automóvel.
        """
        text = f"{nome_arquivo}\n{raw_text}".lower()
        do_markers = (
            "d&o", "directors and officers", "directors & officers",
            "responsabilidade civil de administradores", "administradores e diretores",
            "side a", "side b", "side c", "wrongful act", "ato de gestão",
            "seguro d&o", "seguro de administradores"
        )
        auto_markers = (
            "seguro automóvel", "seguro de automóvel", "condições gerais de automóvel",
            "ramo automóvel", "automóvel casco", "rcf-v", "acidentes pessoais de passageiros",
            "veículo segurado", "chassi", "placa do veículo", "cobertura compreensiva",
            "casco automóvel"
        )
        do_score = sum(1 for marker in do_markers if marker in text)
        auto_score = sum(1 for marker in auto_markers if marker in text)

        if do_score >= 1 and do_score > auto_score:
            return "do"
        if auto_score >= 2 and auto_score > do_score:
            return "auto"
        return "unknown"

    @staticmethod
    def _chunk_text(raw_text: str, max_chars: int = 45000, overlap: int = 3000) -> List[str]:
        """Divide o documento completo em blocos sobrepostos sem descartar o restante do texto."""
        text = raw_text or ""
        if not text:
            return [""]
        if max_chars <= overlap:
            raise ValueError("max_chars deve ser maior que overlap")

        chunks: List[str] = []
        start = 0
        text_len = len(text)

        while start < text_len:
            hard_end = min(start + max_chars, text_len)
            end = hard_end

            # Quando possível, encerra próximo de um marcador de página para preservar contexto.
            if hard_end < text_len:
                page_break = text.rfind("\n--- PÁGINA ", start + max_chars // 2, hard_end)
                if page_break > start:
                    end = page_break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            if end >= text_len:
                break

            next_start = max(end - overlap, start + 1)
            start = next_start

        return chunks or [""]

    @staticmethod
    def _parse_json_object(text: str) -> Optional[Dict[str, Any]]:
        """Extrai um objeto JSON da resposta textual do modelo."""
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if not match:
                return None
            try:
                parsed = json.loads(match.group(0))
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None

    def segment_clauses(self, raw_text: str) -> Dict[str, str]:
        """Segmenta o documento inteiro em seções temáticas usando processamento por chunks."""
        if self.is_available():
            chunks = self._chunk_text(raw_text)
            merged = {
                "dados_gerais": "",
                "coberturas": "",
                "exclusoes": "",
                "valores_e_franquias": "",
                "escopo_e_foro": "",
            }
            successful_chunks = 0

            for idx, chunk in enumerate(chunks, start=1):
                try:
                    prompt = (
                        "Você é um especialista em seguros D&O (Directors and Officers). "
                        "Analise TODO o trecho abaixo, que faz parte de um contrato completo. "
                        "Não invente conteúdo. Classifique apenas texto efetivamente presente "
                        "nas seguintes seções: 'dados_gerais', 'coberturas', 'exclusoes', "
                        "'valores_e_franquias', 'escopo_e_foro'. "
                        "Retorne APENAS um objeto JSON válido, sem markdown. "
                        f"Trecho {idx}/{len(chunks)}:\n\n{chunk}"
                    )
                    response = self.client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt
                    )
                    data = self._parse_json_object(response.text or "")
                    if not data:
                        continue

                    successful_chunks += 1
                    for key in merged:
                        value = data.get(key)
                        if value:
                            merged[key] += (("\n\n" if merged[key] else "") + str(value))
                except Exception as e:
                    logger.warning(
                        f"Falha no chunk {idx}/{len(chunks)} durante segmentação Gemini: {e}"
                    )

            if successful_chunks > 0:
                return merged

        return self._heuristic_segmentation(raw_text)

    def extract_structured_apolice(
        self,
        raw_text: str,
        nome_arquivo: str,
        file_hash: str,
        metodo_extracao: str = "pdfplumber"
    ) -> ApoliceDAO:
        """Consolida a estrutura canônica a partir de todo o documento, processado em chunks."""
        if self.is_available():
            chunks = self._chunk_text(raw_text)
            partials: List[Dict[str, Any]] = []

            for idx, chunk in enumerate(chunks, start=1):
                try:
                    prompt = (
                        "Você é um engenheiro de dados sênior especialista em seguros D&O. "
                        "Extraia SOMENTE informações explicitamente presentes no trecho fornecido. "
                        "Não use conhecimento externo e não preencha campos por padrão. "
                        "Quando um dado não estiver presente no trecho, use null ou []. "
                        "Responda APENAS JSON válido, sem markdown. "
                        "O código do ramo só pode ser informado quando houver evidência textual explícita "
                        "ou uma identificação inequívoca do produto no trecho. "
                        "O tipo de movimento só pode ser informado quando houver indicação explícita.\n\n"
                        "{\n"
                        '  "seguradora": null,\n'
                        '  "segurado": null,\n'
                        '  "numero_apolice": null,\n'
                        '  "vigencia_inicio": null,\n'
                        '  "vigencia_fim": null,\n'
                        '  "premio_total": null,\n'
                        '  "limite_responsabilidade": null,\n'
                        '  "franquia": null,\n'
                        '  "coberturas": [],\n'
                        '  "exclusoes": [],\n'
                        '  "clausulas_especiais": [],\n'
                        '  "retroatividade": null,\n'
                        '  "territorio": null,\n'
                        '  "legislacao_aplicavel": null,\n'
                        '  "cod_ramo": null,\n'
                        '  "ramo_descricao": null,\n'
                        '  "tipo_movimento": null,\n'
                        '  "tipo_movimento_descricao": null\n'
                        "}\n\n"
                        f"Trecho {idx}/{len(chunks)} do documento:\n{chunk}"
                    )
                    response = self.client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt
                    )
                    data = self._parse_json_object(response.text or "")
                    if data:
                        partials.append(data)
                except Exception as e:
                    logger.warning(
                        f"Falha no chunk {idx}/{len(chunks)} durante extração Gemini: {e}"
                    )

            if partials:
                scalar_fields = [
                    "seguradora", "segurado", "numero_apolice",
                    "vigencia_inicio", "vigencia_fim", "premio_total",
                    "limite_responsabilidade", "franquia", "retroatividade",
                    "territorio", "legislacao_aplicavel", "cod_ramo",
                    "ramo_descricao", "tipo_movimento", "tipo_movimento_descricao"
                ]
                list_fields = ["coberturas", "exclusoes", "clausulas_especiais"]

                data_merged: Dict[str, Any] = {}
                for field in scalar_fields:
                    data_merged[field] = next(
                        (
                            item.get(field)
                            for item in partials
                            if item.get(field) not in (None, "", [], {})
                        ),
                        None,
                    )

                for field in list_fields:
                    values: List[str] = []
                    for item in partials:
                        raw_values = item.get(field) or []
                        if not isinstance(raw_values, list):
                            continue
                        for value in raw_values:
                            normalized = str(value).strip()
                            if normalized and normalized not in values:
                                values.append(normalized)
                    data_merged[field] = values

                missing_fields = [
                    field for field in scalar_fields + list_fields
                    if data_merged.get(field) in (None, "", [])
                ]
                confidence = 0.95 * (len(partials) / max(len(chunks), 1))

                return ApoliceDAO(
                    id=file_hash,
                    nome_arquivo=nome_arquivo,
                    data_processamento=__import__("datetime").datetime.now().isoformat(),
                    seguradora=data_merged.get("seguradora"),
                    segurado=data_merged.get("segurado"),
                    numero_apolice=data_merged.get("numero_apolice"),
                    vigencia_inicio=data_merged.get("vigencia_inicio"),
                    vigencia_fim=data_merged.get("vigencia_fim"),
                    premio_total=data_merged.get("premio_total"),
                    limite_responsabilidade=data_merged.get("limite_responsabilidade"),
                    franquia=data_merged.get("franquia"),
                    coberturas=data_merged.get("coberturas", []),
                    exclusoes=data_merged.get("exclusoes", []),
                    clausulas_especiais=data_merged.get("clausulas_especiais", []),
                    retroatividade=data_merged.get("retroatividade"),
                    territorio=data_merged.get("territorio"),
                    legislacao_aplicavel=data_merged.get("legislacao_aplicavel"),
                    cod_ramo=(
                        str(data_merged["cod_ramo"]).strip()[:4]
                        if data_merged.get("cod_ramo") not in (None, "")
                        else None
                    ),
                    ramo_descricao=data_merged.get("ramo_descricao"),
                    tipo_movimento=(
                        str(data_merged["tipo_movimento"]).strip()[:3]
                        if data_merged.get("tipo_movimento") not in (None, "")
                        else None
                    ),
                    tipo_movimento_descricao=data_merged.get("tipo_movimento_descricao"),
                    metodo_extracao=metodo_extracao,
                    confianca_extracao=round(confidence, 3),
                    campos_nao_encontrados=missing_fields,
                )

        return self._heuristic_extractor(raw_text, nome_arquivo, file_hash, metodo_extracao)

    def generate_executive_report(self, comp: ComparisonResult) -> str:
        """Gera parecer executivo narrativo em Markdown (PT-BR) comparando as apólices."""
        if self.is_available():
            try:
                diffs_summary = "\n".join([
                    f"- {d.rotulo}: {comp.apolice_a_nome} = '{d.valor_apolice_a}' | {comp.apolice_b_nome} = '{d.valor_apolice_b}' (Diferença: {d.ha_diferenca})"
                    for d in comp.diffs
                ])
                prompt = (
                    "Você é um consultor e subscritor sênior de seguros D&O (Directors & Officers). "
                    "Elabore um parecer executivo comparativo de alto padrão entre duas apólices com base nos dados fornecidos.\n\n"
                    f"Apólice A: {comp.apolice_a_nome}\n"
                    f"Apólice B: {comp.apolice_b_nome}\n"
                    f"Score de Similaridade: {comp.score_similaridade}%\n"
                    f"Coberturas Exclusivas de A: {comp.coberturas_exclusivas_a}\n"
                    f"Coberturas Exclusivas de B: {comp.coberturas_exclusivas_b}\n"
                    f"Exclusões Exclusivas de A: {comp.exclusoes_exclusivas_a}\n"
                    f"Exclusões Exclusivas de B: {comp.exclusoes_exclusivas_b}\n"
                    f"Comparativo de Campos:\n{diffs_summary}\n\n"
                    "Estruture sua resposta em Markdown profissional com as seguintes seções:\n"
                    "1. ## Resumo Executivo (Visão geral e contexto de contratação)\n"
                    "2. ## Análise de Limites e Franquias (Diferenças financeiras e retenção)\n"
                    "3. ## Confronto de Coberturas e Lacunas de Proteção (O que uma cobre e a outra não)\n"
                    "4. ## Matriz de Riscos e Exclusões Relevantes (Atenção para cláusulas restritivas)\n"
                    "5. ## Recomendação Estratégica (Para o Diretor Jurídico / CFO / Corretor)\n"
                )
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                if response.text:
                    return response.text
            except Exception as e:
                logger.error(f"Erro ao gerar relatório com Gemini: {e}. Gerando relatório via modelo de regras.")

        return self._generate_heuristic_report(comp)

    # -------------------------------------------------------------------------
    # Provedores de Contingência Heurísticos (Resiliência & Modo Offline)
    # -------------------------------------------------------------------------

    def _heuristic_segmentation(self, text: str) -> Dict[str, str]:
        """Segmentação textual baseada em marcadores contratuais padrão D&O."""
        sections = {
            "dados_gerais": "",
            "coberturas": "",
            "exclusoes": "",
            "valores_e_franquias": "",
            "escopo_e_foro": ""
        }
        lines = text.split("\n")
        current_section = "dados_gerais"
        
        for line in lines:
            lower = line.lower()
            if any(term in lower for term in ["cobertura", "garantia", "side a", "side b"]):
                current_section = "coberturas"
            elif any(term in lower for term in ["exclusão", "exclusoes", "riscos excluidos", "nao se aplica"]):
                current_section = "exclusoes"
            elif any(term in lower for term in ["franquia", "lmg", "limite maximo", "premio"]):
                current_section = "valores_e_franquias"
            elif any(term in lower for term in ["foro", "jurisdição", "territorio", "retroatividade"]):
                current_section = "escopo_e_foro"
            
            sections[current_section] += line + "\n"

        return sections

    def _heuristic_extractor(
        self,
        raw_text: str,
        nome_arquivo: str,
        file_hash: str,
        metodo_extracao: str
    ) -> ApoliceDAO:
        """Extrator por expressões regulares e heurísticas securitárias para modo offline/demo."""
        from datetime import datetime

        # Seguradora
        seguradora = None
        if "allianz" in raw_text.lower() or "allianz" in nome_arquivo.lower():
            seguradora = "Allianz Global Corporate & Specialty"
        elif "chubb" in raw_text.lower() or "chubb" in nome_arquivo.lower():
            seguradora = "Chubb Seguros Brasil S.A."
        elif "aig" in raw_text.lower() or "aig" in nome_arquivo.lower():
            seguradora = "AIG Seguros Brasil S.A."
        else:
            match = re.search(r'seguradora\s*[:\-]?\s*([A-Za-z0-9\s\.&]+)', raw_text, re.IGNORECASE)
            seguradora = match.group(1).strip().split('\n')[0] if match else None

        # Segurado
        segurado = None
        candidate = None
        match = re.search(
            r'(?:tomador\s*/\s*segurad[ao]|empresa\s+segurada|tomador|segurad[ao])\s*[:\-]\s*(.+?)(?=\s{2,}ap[oó]lice|\n\s*per[ií]odo|\n\s*ap[oó]lice|\n\s*vig[eê]ncia|\n\s*limite)',
            raw_text,
            re.IGNORECASE | re.DOTALL
        )
        if match:
            candidate = ' '.join(match.group(1).split()).strip()
            candidate = re.sub(r'^[/\s\-]+', '', candidate)
        document_domain = self._detect_document_domain(raw_text, nome_arquivo)
        is_demo_sample = self._is_demo_sample(nome_arquivo)
        is_auto_manual = document_domain == "auto"

        if is_auto_manual:
            if not segurado or len(segurado) > 80 or "art." in segurado.lower() or "tokio" in segurado.lower() or "porto" in segurado.lower():
                segurado = "Condições Gerais de Automóvel (Apólice Coletiva / Individual)"
        else:
            if candidate and 3 < len(candidate) < 80:
                segurado = candidate
            if not segurado:
                if is_demo_sample:
                    match_fallback = re.search(r'(?:techcorp[^\n\r]+)', raw_text, re.IGNORECASE)
                    segurado = match_fallback.group(0).strip() if match_fallback else "TechCorp Brasil Inovações e Soluções Tecnológicas S.A."
                else:
                    segurado = None
        
        segurado = ' '.join(str(segurado).split()).strip()
        if len(segurado) > 80:
            segurado = segurado[:77] + "..."

        # Número da Apólice ou Registro SUSEP
        num_apolice = None
        match_susep = re.search(r'(?:processo\s+susep|susep\s*n[ºo\.]?)\s*[:\-]?\s*([0-9\.\-/]+)', raw_text, re.IGNORECASE)
        match_apolice = re.search(r'(?:ap[oó]lice|proposta)\s*(?:n[ºo\.]?)?\s*[:\-]?\s*([0-9\.\-/]+)', raw_text, re.IGNORECASE)
        
        if match_susep:
            num_apolice = f"Proc. SUSEP {match_susep.group(1).strip()}"
        elif match_apolice:
            num_apolice = match_apolice.group(1).strip()
        else:
            if is_demo_sample:
                num_apolice = "SUSEP 15414.650252/2024-75" if is_auto_manual else "01.0775.000458/01"
            else:
                num_apolice = None

        # Vigência
        vigencia_inicio = None
        vigencia_fim = None
        dates = re.findall(r'\b\d{2}/\d{2}/\d{4}\b', raw_text)
        if len(dates) >= 2:
            vigencia_inicio, vigencia_fim = dates[0], dates[1]
        elif is_demo_sample and is_auto_manual:
            vigencia_inicio = "24h do dia de emissão"
            vigencia_fim = "365 dias (Vigência Anual)"
        elif is_demo_sample:
            vigencia_inicio = "01/01/2026"
            vigencia_fim = "01/01/2027"
        else:
            vigencia_inicio = None
            vigencia_fim = None

        # Limite de Responsabilidade (LMG / FIPE)
        limite = None
        if is_auto_manual:
            limite = "100% Tabela FIPE (Valor de Mercado Referenciado)"
        else:
            match = re.search(r'(?:limite[^\n:]*|lmg|garantia)\s*[:\-]\s*(r\$\s*[\d\.,\s]+)', raw_text, re.IGNORECASE)
            if match:
                limite = match.group(1).strip().split('\n')[0]
            else:
                if is_demo_sample:
                    if "15.000.000" in raw_text:
                        limite = "R$ 15.000.000,00"
                    elif "10.000.000" in raw_text:
                        limite = "R$ 10.000.000,00"
                    elif "5.000.000" in raw_text:
                        limite = "R$ 5.000.000,00"
                    else:
                        limite = "R$ 10.000.000,00"
                else:
                    limite = None

        # Franquia
        franquia = None
        if is_auto_manual:
            franquia = "Franquia Obrigatória Padrão / Reduzida (Casco)"
        else:
            match = re.search(r'(?:franquia|reten[çc][aã]o)\s*[:\-]?\s*(r\$\s*[\d\.,\s]+|isento|sem\s+franquia)', raw_text, re.IGNORECASE)
            if match:
                franquia = match.group(1).strip().split('\n')[0]
            elif is_demo_sample:
                franquia = "R$ 50.000,00 (Isento para Side A)"
            else:
                franquia = None

        # Prêmio Total
        premio = None
        if is_auto_manual:
            premio = "Tarifário Anual conforme Perfil do Condutor"
        else:
            match = re.search(r'(?:pr[eê]mio\s+total|pr[eê]mio\s+l[ií]quido)\s*[:\-]?\s*(r\$\s*[\d\.,\s]+)', raw_text, re.IGNORECASE)
            if match:
                premio = match.group(1).strip().split('\n')[0]
            elif is_demo_sample:
                premio = "R$ 120.000,00"
            else:
                premio = None

        # Retroatividade
        retroatividade = None
        match_retro = re.search(r'(?:data\s+de\s+retroatividade|retroatividade)\s*[:\-]?\s*([^\n\r]+)', raw_text, re.IGNORECASE)
        if match_retro:
            retroatividade = match_retro.group(1).strip()
        else:
            retroatividade = "01/01/2023 (3 anos de retroatividade)" if is_demo_sample else None

        # Território e Foro
        territorio = None
        match_terr = re.search(r'(?:[âa]mbito\s+territorial|territ[oó]rio)\s*[:\-]?\s*([^\n\r]+)', raw_text, re.IGNORECASE)
        if match_terr:
            territorio = match_terr.group(1).strip()
        else:
            if "exceto eua" in raw_text.lower():
                territorio = "Brasil e Jurisdição Mundial (exceto EUA e Canadá)"
            elif "inclusive eua" in raw_text.lower():
                territorio = "Mundial (inclusive EUA e Canadá)"
            elif is_demo_sample:
                territorio = "Brasil e Jurisdição Mundial (exceto EUA e Canadá)"
            else:
                territorio = None

        legislacao = None
        match_foro = re.search(
            r'(?:foro|jurisdi[cç][aã]o|legisla[cç][aã]o(?:s+aplic[aá]vel)?)s*[:-]?s*([^
]{3,160})',
            raw_text,
            re.IGNORECASE
        )
        if match_foro:
            legislacao = match_foro.group(1).strip()
        elif is_demo_sample:
            legislacao = "Legislação Brasileira, Foro da Comarca de São Paulo/SP"

        # Coberturas e Exclusões padrão extraídas do documento
        # Detecção de Ramo SUSEP
        cod_ramo = "0378"
        ramo_desc = "Responsabilidade Civil D&O"
        match_ramo = re.search(r'(?:ramo(?:\s+susep)?|c[oó]d(?:igo)?(?:\s+do)?\s+ramo)\s*[:\-]?\s*([0-9]{4})', raw_text, re.IGNORECASE)
        if match_ramo:
            cod_ramo = match_ramo.group(1).strip()
            from core.variance_engine import get_ramo_name
            ramo_desc = get_ramo_name(cod_ramo)
        elif document_domain == "auto":
            cod_ramo = "0531"
            ramo_desc = "Automóvel - Casco / RCF"
        elif document_domain == "do":
            cod_ramo = "0378"
            ramo_desc = "Responsabilidade Civil D&O"
        else:
            cod_ramo = None
            ramo_desc = None

        # Coberturas e Exclusões padrão extraídas do documento conforme o ramo
        coberturas = []
        exclusoes = []

        if cod_ramo == "0531":
            auto_cobs = [
                "Compreensiva (Colisão, Incêndio e Roubo/Furto)",
                "RCF-V Danos Materiais a Terceiros",
                "RCF-V Danos Corporais a Terceiros",
                "Acidentes Pessoais de Passageiros (APP - Morte e Invalidez)",
                "Assistência 24 Horas com Guincho Ilimitado",
                "Cobertura para Vidros, Faróis, Lanternas e Retrovisores",
                "Carro Reserva em caso de Sinistro de Indenização Integral",
                "Danos Morais e Estéticos Decorrentes de RCF"
            ]
            for c in auto_cobs:
                token = c.split('(')[0].strip()
                if any(word.lower() in raw_text.lower() for word in token.split() if len(word) > 4):
                    coberturas.append(c)
            if not coberturas and is_demo_sample:
                coberturas = auto_cobs[:5]

            auto_excs = [
                "Desgaste natural, corrosão, depreciação pelo uso e falhas mecânicas/elétricas",
                "Condução do veículo sob efeito de álcool, drogas ou entorpecentes",
                "Condutor sem habilitação legal válida ou com CNH suspensa",
                "Uso do veículo para fins diversos do declarado no perfil (ex: transporte remunerado não informado)",
                "Atos de hostilidade, guerra, rebelião, tumultos e comoção pública",
                "Participação em competições, apostas ou provas de velocidade (rachas)"
            ]
            for e in auto_excs:
                token = e.split(',')[0].strip()
                if any(word.lower() in raw_text.lower() for word in token.split() if len(word) > 4):
                    exclusoes.append(e)
            if not exclusoes and is_demo_sample:
                exclusoes = auto_excs[:4]
        else:
            cobs_candidates = [
                "Cobertura Side A (Indivíduos não indenizados pela sociedade)",
                "Cobertura Side B (Reembolso da Sociedade)",
                "Cobertura Side C (Sociedade por ações em reclamações de valores mobiliários)",
                "Custos de Defesa e Honorários Advocatícios Antecipados",
                "Custos de Investigação Regulatória (CVM, BACEN, CADE)",
                "Extensão de Cobertura para Penhora Online e Bloqueio de Bens",
                "Despesas de Publicidade e Gestão de Crise de Imagem",
                "Multas e Penalidades Civis Seguráveis",
                "Cobertura Automática para Novas Subsidiárias",
                "Prazo Complementar de Notificação (12 a 36 meses)"
            ]
            for c in cobs_candidates:
                token = c.split('(')[0].strip()
                if any(word.lower() in raw_text.lower() for word in token.split() if len(word) > 4):
                    coberturas.append(c)
            if not coberturas and is_demo_sample:
                coberturas = cobs_candidates[:6]

            excs_candidates = [
                "Atos dolosos, fraude comprovada ou conduta criminal transitada em julgado",
                "Obtenção de lucro ou vantagem financeira indevida",
                "Danos corporais, morte e danos materiais diretos",
                "Poluição e contaminação ambiental (salvo custos de defesa emergenciais)",
                "Reclamações anteriores ou fatos conhecidos antes da retroatividade",
                "Litígios societários entre segurados (Insured vs. Insured)",
                "Violação de leis de valores mobiliários norte-americanas (SEC / Rule 10b-5)"
            ]
            for e in excs_candidates:
                token = e.split(',')[0].strip()
                if any(word.lower() in raw_text.lower() for word in token.split() if len(word) > 4):
                    exclusoes.append(e)
            if not exclusoes and is_demo_sample:
                exclusoes = excs_candidates[:5]

        lower_raw = raw_text.lower()
        if "endosso de cobrança" in lower_raw or "endosso adicional" in lower_raw:
            tipo_mov = "102"
            tipo_desc = "Endosso de cobrança adicional de prêmio"
        elif "cancelamento" in lower_raw and "restituição" in lower_raw:
            tipo_mov = "104"
            tipo_desc = "Cancelamento de Apólice com restituição de prêmio"
        elif "cancelamento" in lower_raw:
            tipo_mov = "106"
            tipo_desc = "Cancelamento de Apólice sem restituição de prêmio"
        elif "sem movimentação" in lower_raw or "sem prêmio" in lower_raw:
            tipo_mov = "108"
            tipo_desc = "Endosso sem movimentação de prêmio"
        elif "endosso" in lower_raw or "endosso" in nome_arquivo.lower():
            tipo_mov = "102"
            tipo_desc = "Endosso de cobrança adicional de prêmio"
        else:
            tipo_mov = "101"
            tipo_desc = "Emissão de Apólice"

        return ApoliceDAO(
            id=file_hash,
            nome_arquivo=nome_arquivo,
            data_processamento=datetime.now().isoformat(),
            seguradora=seguradora,
            segurado=segurado,
            numero_apolice=num_apolice,
            vigencia_inicio=vigencia_inicio,
            vigencia_fim=vigencia_fim,
            premio_total=premio,
            limite_responsabilidade=limite,
            franquia=franquia,
            coberturas=coberturas,
            exclusoes=exclusoes,
            clausulas_especiais=["Cláusula de Não Imputação Mútua de Dolo", "Bilateralidade no cancelamento"],
            retroatividade=retroatividade,
            territorio=territorio,
            legislacao_aplicavel=legislacao,
            cod_ramo=cod_ramo,
            ramo_descricao=ramo_desc,
            tipo_movimento=tipo_mov,
            tipo_movimento_descricao=tipo_desc,
            metodo_extracao="mock_fallback" if is_demo_sample else "heuristic_fallback",
            confianca_extracao=0.88 if is_demo_sample else 0.35,
            campos_nao_encontrados=[
                campo for campo, valor in {
                    "seguradora": seguradora,
                    "segurado": segurado,
                    "numero_apolice": num_apolice,
                    "vigencia_inicio": vigencia_inicio,
                    "vigencia_fim": vigencia_fim,
                    "premio_total": premio,
                    "limite_responsabilidade": limite,
                    "franquia": franquia,
                    "coberturas": coberturas,
                    "exclusoes": exclusoes,
                    "retroatividade": retroatividade,
                    "territorio": territorio,
                    "legislacao_aplicavel": legislacao,
                    "cod_ramo": cod_ramo,
                }.items() if valor in (None, "", [])
            ]
        )

    def generate_audit_variance_justification(self, report: Any) -> str:
        """Gera nota explicativa e justificativa de auditoria via Gemini 2.0 Flash para o FIP/SUSEP."""
        if self.is_available() and report.ramo_maior_ofensor and report.sinistro_maior_ofensor:
            try:
                prompt = (
                    "Você é um atuário e contador sênior especialista em regulação SUSEP e IFRS 17 / CPC 50. "
                    "Elabore uma nota explicativa técnica e formal de auditoria contábil justificando a variação "
                    "na provisão de sinistros (PSL) do período com base nos dados a seguir:\n\n"
                    f"- Período: {report.periodo_referencia}\n"
                    f"- Saldo Anterior Geral: R$ {report.total_anterior_geral:,.2f}\n"
                    f"- Saldo Atual Geral: R$ {report.total_atual_geral:,.2f}\n"
                    f"- Variação Líquida Global: R$ {report.delta_global:,.2f} ({report.delta_global_percentual:.2f}%)\n"
                    f"- Ramo Maior Ofensor: {report.ramo_maior_ofensor.cod_ramo} - {report.ramo_maior_ofensor.ramo_nome} "
                    f"(Impacto: R$ {report.ramo_maior_ofensor.delta_absoluto:,.2f}, Share: {report.ramo_maior_ofensor.share_na_variacao_total:.1f}%)\n"
                    f"- Sinistro Maior Ofensor: {report.sinistro_maior_ofensor.numero_sinistro} (Apólice {report.sinistro_maior_ofensor.numero_apolice}, "
                    f"Segurado: {report.sinistro_maior_ofensor.segurado}, Impacto: R$ {report.sinistro_maior_ofensor.delta_variacao:,.2f}, "
                    f"Causa: {report.sinistro_maior_ofensor.causa_sinistro})\n\n"
                    "Estruture a nota em Markdown formal para SUSEP e Auditoria Externa contendo:\n"
                    "1. Contexto e Movimentação Geral das Provisões Técnicas\n"
                    "2. Justificativa Detalhada do Ramo Maior Ofensor\n"
                    "3. Análise Individual do Evento de Maior Materialidade (Maior Ofensor)\n"
                    "4. Parecer de Conformidade com as Circulares da SUSEP\n"
                )
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt
                )
                if response.text:
                    return response.text
            except Exception as e:
                logger.error(f"Erro ao gerar justificativa de auditoria com Gemini: {e}")

        return report.justificativa_auditoria_markdown

    def _generate_heuristic_report(self, comp: ComparisonResult) -> str:
        """Gera um relatório executivo estruturado caso a API do Gemini esteja inacessível."""
        diff_table = "| Campo | " + comp.apolice_a_nome + " | " + comp.apolice_b_nome + " | Status |\n"
        diff_table += "|---|---|---|---|\n"
        for d in comp.diffs:
            status_icon = "✅ Igual" if not d.ha_diferenca else "⚠️ Divergente"
            diff_table += f"| **{d.rotulo}** | {d.valor_apolice_a or '-'} | {d.valor_apolice_b or '-'} | {status_icon} |\n"

        cobs_a_str = "\n".join([f"- **{c}**" for c in comp.coberturas_exclusivas_a]) or "_Nenhuma cobertura exclusiva identificada._"
        cobs_b_str = "\n".join([f"- **{c}**" for c in comp.coberturas_exclusivas_b]) or "_Nenhuma cobertura exclusiva identificada._"

        return f"""# Relatório Técnico-Comparativo de Apólices D&O
**Análise de Conformidade e Gestão de Riscos Corporativos**  
*InsurMinds Apólice Analyzer · Inteligência Analítica em Seguros*

---

## 1. Resumo Executivo

O presente parecer consolida a comparação analítica entre as propostas de seguro de Responsabilidade Civil de Administradores (D&O) emitidas por **{comp.apolice_a_nome}** e **{comp.apolice_b_nome}**. 

O índice global de similaridade apurado entre as duas apólices é de **{comp.score_similaridade}%**, refletindo uma estrutura geral alinhada com as práticas regulatórias da SUSEP, porém com **diferenças críticas em limites financeiros, franquias operacionais e extensões de cobertura** que impactam diretamente a blindagem do patrimônio pessoal dos administradores.

---

## 2. Matriz Comparativa de Condições Particulares

A tabela abaixo resume os parâmetros fundamentais extraídos e confrontados:

{diff_table}

---

## 3. Confronto de Coberturas e Lacunas de Proteção

### 🛡️ Coberturas Exclusivas da {comp.apolice_a_nome}:
{cobs_a_str}

### 🛡️ Coberturas Exclusivas da {comp.apolice_b_nome}:
{cobs_b_str}

### 🤝 Coberturas em Comum:
{chr(10).join([f"- {c}" for c in comp.coberturas_comuns]) or "_Ambas cobrem as cláusulas essenciais Side A e Side B._"}

---

## 4. Análise de Riscos e Exclusões

As exclusões contratuais delimitam as hipóteses em que os administradores não terão suporte financeiro da seguradora:
- **Exclusões Exclusivas ({comp.apolice_a_nome}):** {', '.join(comp.exclusoes_exclusivas_a) if comp.exclusoes_exclusivas_a else 'Nenhuma exclusão assimétrica relevante.'}
- **Exclusões Exclusivas ({comp.apolice_b_nome}):** {', '.join(comp.exclusoes_exclusivas_b) if comp.exclusoes_exclusivas_b else 'Nenhuma exclusão assimétrica relevante.'}
- **Ponto de Atenção:** Recomenda-se especial cautela quanto a exigências de trânsito em julgado para imputação de atos dolosos e cobertura expressa para processos instaurados pela CVM ou autoridades reguladoras.

---

## 5. Recomendação Estratégica

Com base no levantamento quantitativo e qualitativo:
1. **Para Empresas em Fase de Crescimento / IPO:** A apólice com maior limite agregado e cobertura ampla de investigação regulatória deve ser priorizada.
2. **Otimização de Custos:** Caso a diferença de prêmio supere 25%, avaliar se as coberturas exclusivas justificam o diferencial financeiro.
3. **Harmonização Contratual:** Negociar com o corretor a inclusão de endosso para extensão de retroatividade ilimitada na proposta vencedora.

---
*Relatório gerado automaticamente pelo InsurMinds Apólice Analyzer em {comp.data_comparacao[:10]}*.
"""


# Instância padrão singleton
llm_client = GeminiClient()
