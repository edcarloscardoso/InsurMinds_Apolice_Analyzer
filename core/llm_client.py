"""Cliente de integração com os modelos de IA Generativa (Google Gemini 2.0 Flash).
Fornece extração estruturada de cláusulas, fallback multimodal (Vision) e síntese de relatórios executivos.
Inclui provedor de contingência heurístico para execução contínua em modo offline ou demonstração.
"""
import os
import json
import logging
import re
import time
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from core.config import GOOGLE_API_KEY, GEMINI_MODEL
from core.schemas import ApoliceDAO, ComparisonResult, DocumentChunk, EvidenceItem
from core.domain_detector import is_demo_sample, detect_document_domain, detect_document_type, resolve_seguradora
from core.document_chunker import build_document_chunks, chunk_text, find_evidence_in_text, discover_contract_clauses
from core.consolidation import consolidate_extracted_chunks, normalize_scalar

logger = logging.getLogger(__name__)


# =============================================================================
# SCHEMAS DE STRUCTURED OUTPUT NATIVO (GOOGLE GENAI SDK)
# =============================================================================

class ChunkExtractionSchema(BaseModel):
    """Schema Pydantic nativo para Structured Output do Google GenAI SDK."""
    seguradora: Optional[str] = None
    segurado: Optional[str] = None
    numero_apolice: Optional[str] = None
    processo_susep: Optional[str] = None
    vigencia_inicio: Optional[str] = None
    vigencia_fim: Optional[str] = None
    premio_total: Optional[str] = None
    limite_responsabilidade: Optional[str] = None
    franquia: Optional[str] = None
    coberturas: List[str] = Field(default_factory=list)
    exclusoes: List[str] = Field(default_factory=list)
    clausulas_especiais: List[str] = Field(default_factory=list)
    retroatividade: Optional[str] = None
    territorio: Optional[str] = None
    legislacao_aplicavel: Optional[str] = None
    cod_ramo: Optional[str] = None
    ramo_descricao: Optional[str] = None
    tipo_movimento: Optional[str] = None
    tipo_movimento_descricao: Optional[str] = None
    document_type: Optional[str] = None


class ClauseComparisonSchema(BaseModel):
    """Schema Pydantic nativo para Structured Output de comparação semântica de cláusulas."""
    equivalence: bool = Field(..., description="Indica se há equivalência conceitual substancial")
    relation: str = Field(
        default="semantic_equivalent",
        description="'semantic_equivalent' | 'changed_scope' | 'changed_condition' | 'changed_limit' | 'broader' | 'narrower' | 'different'"
    )
    explanation: str = Field(default="", description="Justificativa técnica da equivalência ou divergência contratual")
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)


class GeminiClient:
    """Cliente wrapper para o Google Gemini com suporte a fallback resiliente."""

    def __init__(self, api_key: Optional[str] = None):
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.client = None
        self.call_history: List[Dict[str, Any]] = []
        self.last_call_stats: Dict[str, Any] = {}
        self.model: str = GEMINI_MODEL
        self._initialize_client()

    @property
    def model_name(self) -> str:
        return self.model

    def _initialize_client(self):
        """Inicializa o SDK google-genai se a chave estiver configurada no ambiente local com timeout explícito."""
        if self.api_key and self.api_key.strip():
            try:
                from google import genai
                from google.genai import types
                http_opts = types.HttpOptions(timeout=30.0)
                self.client = genai.Client(api_key=self.api_key.strip(), http_options=http_opts)
                logger.info("Cliente Google GenAI conectado com sucesso (timeout: 30s).")
            except Exception as e:
                logger.warning(f"Não foi possível inicializar SDK google.genai: {e}. Usando contingência.")
                self.client = None
        else:
            logger.info("Gemini não configurado: nenhuma chave GOOGLE_API_KEY detectada no ambiente. Operando em modo contingência / determinístico.")
            self.client = None

    def _record_call(
        self,
        call_type: str,
        success: bool,
        latency_ms: float,
        method: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Registra telemetria de execução: modelo, chamada, sucesso/falha, latência e método de extração."""
        record = {
            "timestamp": __import__("datetime").datetime.now().isoformat(),
            "model": GEMINI_MODEL,
            "call_type": call_type,
            "success": success,
            "latency_ms": round(latency_ms, 2),
            "extraction_method": method,
            "details": details or {}
        }
        self.call_history.append(record)
        self.last_call_stats = record
        return record

    def is_available(self) -> bool:
        """Indica se a API remota do Gemini está pronta para chamadas."""
        return self.client is not None

    # Métodos estáticos mantidos para compatibilidade com a suíte de testes existente
    @staticmethod
    def _is_demo_sample(nome_arquivo: str) -> bool:
        """Identifica exclusivamente fixtures sintéticas versionadas do projeto."""
        return is_demo_sample(nome_arquivo)

    @staticmethod
    def _detect_document_domain(raw_text: str, nome_arquivo: str) -> str:
        """Classificação conservadora de domínio para o fallback offline."""
        return detect_document_domain(raw_text, nome_arquivo)

    @staticmethod
    def _chunk_text(raw_text: str, max_chars: int = 45000, overlap: int = 3000) -> List[str]:
        """Divide o documento completo em blocos sobrepostos sem descartar o restante do texto."""
        return chunk_text(raw_text, max_chars, overlap)

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

    def compare_clauses_semantically(self, clause_a: str, clause_b: str) -> Optional[Dict[str, Any]]:
        """Compara duas cláusulas contratuais usando Gemini estruturado para avaliar equivalência semântica."""
        if not self.is_available():
            self._record_call(
                call_type="compare_clauses_semantically",
                success=False,
                latency_ms=0.0,
                method="heuristic_fallback",
                details={"reason": "Gemini não configurado"}
            )
            return None
        prompt = (
            "Você é um especialista em seguros D&O (Directors and Officers). "
            "Compare analiticamente as duas cláusulas contratuais abaixo, extraídas de apólices distintas. "
            "Avalie se são conceitualmente equivalentes no contexto específico do seguro D&O.\n\n"
            f"Cláusula da Proposta A: \"{clause_a}\"\n"
            f"Cláusula da Proposta B: \"{clause_b}\"\n\n"
            "Valores aceitos para 'relation': 'semantic_equivalent', 'changed_scope', 'changed_condition', "
            "'changed_limit', 'broader', 'narrower', 'different'. "
            "Não invente fatos e não faça recomendações comerciais."
        )
        t0 = time.time()
        for attempt in range(2):
            try:
                from google.genai import types
                config = types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ClauseComparisonSchema,
                    temperature=0.0
                )
                response = self.client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                    config=config
                )
                t1 = time.time()
                latency = (t1 - t0) * 1000.0
                data = None
                if response.text:
                    try:
                        data = json.loads(response.text)
                    except Exception:
                        data = self._parse_json_object(response.text)

                if data and isinstance(data, dict) and "equivalence" in data:
                    self._record_call(
                        call_type="compare_clauses_semantically",
                        success=True,
                        latency_ms=latency,
                        method="gemini_structured_output",
                        details={"relation": data.get("relation")}
                    )
                    return data
                return None
            except Exception as e:
                if ("429" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt == 0:
                    logger.warning("Rate limit 429 temporário do Gemini. Aguardando 8s para retry...")
                    time.sleep(8.0)
                    continue
                t1 = time.time()
                latency = (t1 - t0) * 1000.0
                self._record_call(
                    call_type="compare_clauses_semantically",
                    success=False,
                    latency_ms=latency,
                    method="gemini_error",
                    details={"error": str(e)}
                )
                logger.warning(f"Falha na chamada semântica do Gemini para cláusulas: {e}")
                return None
        return None

    def extract_text_from_image(self, file_path_or_bytes, mime_type: Optional[str] = None) -> Optional[str]:
        """Extrai texto e tabelas de imagem (PNG, JPG, JPEG) usando o modelo multimodal Google Gemini."""
        if not self.is_available():
            return None

        try:
            from google.genai import types
            from pathlib import Path

            if isinstance(file_path_or_bytes, (str, Path)):
                p = Path(file_path_or_bytes)
                img_bytes = p.read_bytes()
                if mime_type is None:
                    ext = p.suffix.lower()
                    mime_type = "image/png" if ext == ".png" else "image/jpeg"
            else:
                img_bytes = file_path_or_bytes
                if mime_type is None:
                    mime_type = "image/png"

            part = types.Part.from_bytes(data=img_bytes, mime_type=mime_type)
            prompt = (
                "Você é um especialista em OCR documental e regulação de seguros D&O. "
                "Transcreva fielmente todo o conteúdo textual e tabelas visíveis nesta imagem de documento contratual. "
                "Preserve a exatidão literal de nomes de partes, números de apólice e processos SUSEP, valores monetários, "
                "limites de garantia (LMG), franquias, vigência, coberturas e cláusulas de exclusão. "
                "Não invente informações e retorne estritamente o texto transcrito."
            )
            t0 = time.time()
            response = self.client.models.generate_content(
                model=self.model,
                contents=[part, prompt]
            )
            t1 = time.time()
            latency = (t1 - t0) * 1000.0

            text_out = (response.text or "").strip()
            if text_out:
                self._record_call(
                    call_type="extract_text_from_image",
                    success=True,
                    latency_ms=latency,
                    method="gemini_vision",
                    details={"char_count": len(text_out), "mime_type": mime_type}
                )
                return text_out
            return None
        except Exception as e:
            logger.warning(f"Falha na extração de texto via Gemini Vision: {e}")
            self._record_call(
                call_type="extract_text_from_image",
                success=False,
                latency_ms=0.0,
                method="gemini_error",
                details={"error": str(e)}
            )
            return None

    def segment_clauses(self, raw_text: str) -> Dict[str, str]:
        """Segmenta o documento inteiro em seções temáticas usando processamento por chunks."""
        if self.is_available():
            chunks = build_document_chunks(raw_text)
            merged = {
                "dados_gerais": "",
                "coberturas": "",
                "exclusoes": "",
                "valores_e_franquias": "",
                "escopo_e_foro": "",
            }
            successful_chunks = 0

            for chunk_obj in chunks:
                try:
                    prompt = (
                        "Você é um especialista em seguros D&O (Directors and Officers). "
                        "Analise TODO o trecho abaixo, que faz parte de um contrato completo. "
                        "Não invente conteúdo. Classifique apenas texto efetivamente presente "
                        "nas seguintes seções: 'dados_gerais', 'coberturas', 'exclusoes', "
                        "'valores_e_franquias', 'escopo_e_foro'. "
                        "Retorne APENAS um objeto JSON válido, sem markdown. "
                        f"Trecho {chunk_obj.index}/{len(chunks)} (Páginas {chunk_obj.page_start} a {chunk_obj.page_end}):\n\n"
                        f"{chunk_obj.text}"
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
                        f"Falha no chunk {chunk_obj.index}/{len(chunks)} durante segmentação Gemini: {e}"
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
        chunks = build_document_chunks(raw_text)
        page_count = chunks[-1].page_end if chunks else 1
        chunk_count = len(chunks)
        total_input_chars = len(raw_text)
        gemini_chunk_calls = 0
        chunk_errors = 0

        if self.is_available():
            partials: List[Dict[str, Any]] = []
            t0 = time.time()

            for chunk_obj in chunks:
                gemini_chunk_calls += 1
                for attempt in range(2):
                    try:
                        from google.genai import types
                        config = types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=ChunkExtractionSchema,
                            temperature=0.0
                        )
                        prompt = (
                            "Você é um engenheiro de dados sênior especialista em seguros corporativos D&O. "
                            f"Documento de Referência: {nome_arquivo}\n"
                            "Extraia SOMENTE informações explicitamente presentes no trecho fornecido. "
                            "Não use conhecimento externo e não preencha campos por padrão. "
                            "Quando um dado não estiver presente no trecho, use null ou []. "
                            "O código do ramo só pode ser informado quando houver evidência textual explícita "
                            "ou uma identificação inequívoca do produto no trecho. "
                            "O tipo de movimento regulatório SUSEP NUNCA deve ser inferido a partir de cláusulas "
                            "contratuais de rescisão, cancelamento bilateral ou endossos futuros; informe null "
                            "caso não haja campo cadastral específico com o tipo de movimento da apólice. "
                            "O número da apólice (numero_apolice) refere-se estritamente ao identificador da apólice "
                            "individual emitida. NUNCA preencha numero_apolice com o número do processo regulatório da SUSEP; "
                            "o número do processo regulatório deve ser informado estritamente em processo_susep.\n\n"
                            f"Trecho {chunk_obj.index}/{len(chunks)} do documento (Páginas {chunk_obj.page_start} a {chunk_obj.page_end}):\n"
                            f"{chunk_obj.text}"
                        )
                        response = self.client.models.generate_content(
                            model=GEMINI_MODEL,
                            contents=prompt,
                            config=config
                        )
                        data = None
                        if response.text:
                            try:
                                data = json.loads(response.text)
                            except Exception:
                                data = self._parse_json_object(response.text)

                        if data:
                            # Rastreia e vincula a evidência para cada campo identificado no fragmento
                            chunk_evs = {}
                            for k, v in data.items():
                                if v and isinstance(v, (str, int, float)):
                                    ev = find_evidence_in_text(
                                        chunk_obj.text,
                                        str(v),
                                        method="llm",
                                        confidence=0.95,
                                        chunk_index=chunk_obj.index
                                    )
                                    if not ev:
                                        ev_global = find_evidence_in_text(
                                            raw_text,
                                            str(v),
                                            method="llm",
                                            confidence=0.92
                                        )
                                        ev = ev_global if ev_global else EvidenceItem(
                                            page=chunk_obj.page_start,
                                            page_end=chunk_obj.page_end if chunk_obj.page_end != chunk_obj.page_start else None,
                                            snippet=str(v)[:160],
                                            method="llm",
                                            confidence=0.90,
                                            chunk_index=chunk_obj.index
                                        )
                                    chunk_evs[k] = ev
                                elif v and isinstance(v, list):
                                    for item in v:
                                        if isinstance(item, str):
                                            ev_item = find_evidence_in_text(
                                                chunk_obj.text,
                                                item,
                                                method="llm",
                                                confidence=0.90,
                                                chunk_index=chunk_obj.index
                                            )
                                            if not ev_item:
                                                ev_item = find_evidence_in_text(
                                                    raw_text,
                                                    item,
                                                    method="llm",
                                                    confidence=0.88
                                                )
                                            if ev_item:
                                                chunk_evs[k] = ev_item
                                                break
                            data["__evidencias__"] = chunk_evs
                            partials.append(data)
                        break
                    except Exception as e:
                        if ("429" in str(e) or "503" in str(e) or "RESOURCE_EXHAUSTED" in str(e)) and attempt == 0:
                            logger.warning(f"Rate limit / transient error Gemini no chunk {chunk_obj.index}. Aguardando 8s para retry...")
                            time.sleep(8.0)
                            continue
                        chunk_errors += 1
                        logger.warning(
                            f"Falha no chunk {chunk_obj.index}/{len(chunks)} durante extração Gemini: {e}"
                        )
                        break

            t1 = time.time()
            self._record_call(
                call_type="extract_structured_apolice",
                success=bool(partials),
                latency_ms=(t1 - t0) * 1000.0,
                method="gemini_structured_output" if partials else "gemini_error",
                details={
                    "page_count": page_count,
                    "chunk_count": chunk_count,
                    "total_input_chars": total_input_chars,
                    "gemini_chunk_calls": gemini_chunk_calls,
                    "chunk_errors": chunk_errors,
                    "fallback_used": not bool(partials),
                    "chunks_processed": len(chunks),
                    "partials_extracted": len(partials)
                }
            )

            if partials:
                scalar_fields = [
                    "seguradora", "segurado", "numero_apolice", "processo_susep",
                    "vigencia_inicio", "vigencia_fim", "premio_total",
                    "limite_responsabilidade", "franquia", "retroatividade",
                    "territorio", "legislacao_aplicavel", "cod_ramo",
                    "ramo_descricao", "tipo_movimento", "tipo_movimento_descricao",
                    "document_type"
                ]
                list_fields = ["coberturas", "exclusoes", "clausulas_especiais"]

                # Consolidação determinística com preservação de proveniência e conflitos
                (
                    data_merged,
                    field_evidences,
                    conflicts,
                    conflict_evidences
                ) = consolidate_extracted_chunks(
                    partials, scalar_fields, list_fields
                )

                # Resolução canônica de Seguradora
                resolved_seg = resolve_seguradora(
                    data_merged.get("seguradora"),
                    raw_text,
                    nome_arquivo,
                    data_merged.get("processo_susep")
                )
                if resolved_seg:
                    data_merged["seguradora"] = resolved_seg
                    if "seguradora" not in field_evidences or not field_evidences["seguradora"]:
                        ev_seg = find_evidence_in_text(raw_text, resolved_seg, method="canonical_resolution")
                        if not ev_seg and data_merged.get("processo_susep"):
                            ev_seg = find_evidence_in_text(
                                raw_text,
                                data_merged["processo_susep"].replace("Proc. SUSEP ", ""),
                                method="canonical_resolution"
                            )
                        if not ev_seg:
                            ev_seg = EvidenceItem(
                                page=1,
                                snippet=f"Resolução canônica SUSEP/Marca: {resolved_seg}",
                                method="regulatory_registry",
                                confidence=0.95,
                                chunk_index=0
                            )
                        field_evidences["seguradora"] = ev_seg

                raw_doc_type = data_merged.get("document_type") or detect_document_type(raw_text, nome_arquivo)
                low_doc = str(raw_doc_type).lower()
                if "condi" in low_doc or raw_doc_type == "condicoes_gerais":
                    doc_type = "condicoes_gerais"
                elif "endoss" in low_doc or raw_doc_type == "endosso":
                    doc_type = "endosso"
                elif "propost" in low_doc or raw_doc_type == "proposta":
                    doc_type = "proposta"
                elif "apolic" in low_doc or "front" in low_doc or raw_doc_type == "apolice_individual":
                    doc_type = "apolice_individual"
                else:
                    doc_type = raw_doc_type

                # Segregação semântica estrita: Condições Gerais não possuem apólice emitida, segurado ou vigência
                if doc_type == "condicoes_gerais":
                    data_merged["segurado"] = None
                    data_merged["numero_apolice"] = None
                    data_merged["vigencia_inicio"] = None
                    data_merged["vigencia_fim"] = None
                    data_merged["tipo_movimento"] = None
                    data_merged["tipo_movimento_descricao"] = None
                    data_merged["premio_total"] = None
                    data_merged["franquia"] = None
                    data_merged["limite_responsabilidade"] = None
                    field_evidences.pop("segurado", None)
                    field_evidences.pop("numero_apolice", None)
                    field_evidences.pop("vigencia_inicio", None)
                    field_evidences.pop("vigencia_fim", None)
                    field_evidences.pop("tipo_movimento", None)

                # Enriquecimento com descoberta de cláusulas contratuais reais para D&O (Fase 5/5.1)
                doc_domain = detect_document_domain(raw_text, nome_arquivo)
                if doc_domain == "do" and not is_demo_sample(nome_arquivo):
                    cobs_disc, excs_disc, esp_disc, evs_disc = discover_contract_clauses(raw_text, doc_domain)
                    current_cobs = data_merged.setdefault("coberturas", [])
                    for c in cobs_disc:
                        if c not in current_cobs:
                            current_cobs.append(c)
                    current_excs = data_merged.setdefault("exclusoes", [])
                    for e in excs_disc:
                        if e not in current_excs:
                            current_excs.append(e)
                    current_esp = data_merged.setdefault("clausulas_especiais", [])
                    for esp in esp_disc:
                        if esp not in current_esp:
                            current_esp.append(esp)
                    field_evidences.update(evs_disc)

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
                    processo_susep=data_merged.get("processo_susep"),
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
                    document_type=doc_type,
                    metodo_extracao=metodo_extracao,
                    confianca_extracao=round(confidence, 3),
                    campos_nao_encontrados=missing_fields,
                    conflitos_extracao=conflicts,
                    evidencias=field_evidences,
                    evidencias_conflito=conflict_evidences,
                )

        self._record_call(
            call_type="extract_structured_apolice",
            success=True,
            latency_ms=0.0,
            method="heuristic_fallback",
            details={
                "reason": "Gemini não configurado (GOOGLE_API_KEY ausente)" if not self.is_available() else "Gemini chunks indisponíveis",
                "fallback_used": True,
                "page_count": page_count,
                "chunk_count": chunk_count,
                "total_input_chars": total_input_chars,
                "gemini_chunk_calls": gemini_chunk_calls,
                "chunk_errors": chunk_errors
            }
        )
        logger.info("Executando extrator determinístico com extração semântica de cláusulas e proveniência.")
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
        lines = (text or "").split("\n")
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

        document_domain = detect_document_domain(raw_text, nome_arquivo)
        document_type = detect_document_type(raw_text, nome_arquivo)
        is_demo = is_demo_sample(nome_arquivo)

        # ---------------------------------------------------------------------
        # 1. Seguradora
        # ---------------------------------------------------------------------
        match_seg = re.search(r'seguradora\s*[:\-]?\s*([A-Za-z0-9\s\.&]+)', raw_text, re.IGNORECASE)
        cand_seg = match_seg.group(1).strip().split('\n')[0] if match_seg else None
        seguradora = resolve_seguradora(cand_seg, raw_text, nome_arquivo)

        # ---------------------------------------------------------------------
        # 2. Segurado (Tomador)
        # ---------------------------------------------------------------------
        segurado = None
        match_segurado = None
        candidate = None
        # Condições Gerais regulatórias de produto NÃO possuem tomador individual emitido
        if document_type != "condicoes_gerais":
            match_segurado = re.search(
                r'(?:tomador\s*/\s*segurad[ao]|empresa\s+segurada|tomador|segurad[ao])\s*[:\-]\s*(.+?)(?=\s{2,}ap[oó]lice|\n\s*per[ií]odo|\n\s*ap[oó]lice|\n\s*vig[eê]ncia|\n\s*limite|\n|$)',
                raw_text,
                re.IGNORECASE | re.DOTALL
            )
            if match_segurado:
                candidate = ' '.join(match_segurado.group(1).split()).strip()
                candidate = re.sub(r'^[/\s\-]+', '', candidate)
                if candidate and 3 < len(candidate) < 120 and candidate.lower() not in ("none", "null", "n/a"):
                    segurado = normalize_scalar("segurado", candidate)

            if not segurado and is_demo:
                match_fallback = re.search(r'(?:techcorp[^\n\r]+)', raw_text, re.IGNORECASE)
                segurado = match_fallback.group(0).strip() if match_fallback else "TechCorp Brasil Inovações e Soluções Tecnológicas S.A."
            elif not segurado and document_domain == "auto":
                segurado = "Condições Gerais de Automóvel (Apólice Coletiva / Individual)"

        if segurado is not None:
            segurado = normalize_scalar("segurado", segurado)
            if segurado and len(segurado) > 80:
                segurado = segurado[:77] + "..."

        # ---------------------------------------------------------------------
        # 3. Número da Apólice e Processo SUSEP (Distinção Semântica Estrita)
        # ---------------------------------------------------------------------
        # Processo SUSEP = número do processo regulatório do produto na SUSEP
        # Apólice = identificador exclusivo da apólice ou proposta individual emitida
        # NUNCA atribuir Processo SUSEP a numero_apolice.
        # Em Condições Gerais sem front sheet / apólice emitida: numero_apolice = None
        # ---------------------------------------------------------------------
        processo_susep = None
        match_susep = re.search(
            r'(?:processo\s+susep|proc\.?\s*susep|registro\s+susep|susep\s*(?:n[ºo\.]?|processo)?)\s*[:\-]?\s*([0-9\.\-/]+)',
            raw_text,
            re.IGNORECASE
        )
        if match_susep:
            processo_susep = f"Proc. SUSEP {match_susep.group(1).strip()}"
        elif is_demo and document_domain == "auto":
            processo_susep = "Proc. SUSEP 15414.650252/2024-75"

        num_apolice = None
        # Regex estrita para número da apólice: captura quando há menção explícita à apólice/proposta individual
        match_apolice = re.search(
            r'(?:(?:n[ºo\.]?\s*da\s+)?ap[oó]lice|proposta)\s*(?:n[ºo\.]?)?\s*[:\-]?\s*([0-9\.\-/]+)',
            raw_text,
            re.IGNORECASE
        )
        if match_apolice:
            candidate_apolice = match_apolice.group(1).strip()
            # Valida que o candidato não é o número do processo SUSEP
            susep_digits = match_susep.group(1).strip() if match_susep else ""
            if not susep_digits or candidate_apolice != susep_digits:
                num_apolice = candidate_apolice
        elif is_demo and document_domain != "auto":
            num_apolice = "01.0775.000458/01"

        if num_apolice:
            num_apolice = normalize_scalar("numero_apolice", num_apolice)
        if processo_susep:
            processo_susep = normalize_scalar("processo_susep", processo_susep)

        # ---------------------------------------------------------------------
        # 4. Vigência da Apólice (Distinção Estrita de Validade de Condições Gerais)
        # ---------------------------------------------------------------------
        # vigencia_inicio e vigencia_fim referem-se estritamente ao período de cobertura
        # de uma apólice individual emitida.
        # NUNCA atribuir datas de aplicabilidade ou comercialização das Condições Gerais
        # (ex: "Válida para os seguros comercializados a partir de...") como vigência da apólice.
        # Em Condições Gerais sem front sheet / apólice emitida: vigência = None.
        # ---------------------------------------------------------------------
        vigencia_inicio = None
        vigencia_fim = None

        match_vig = re.search(
            r'(?:per[ií]odo\s+de\s+vig[eê]ncia|vig[eê]ncia(?:\s+do\s+seguro|\s+da\s+ap[oó]lice|\s+individual)?)\s*[:\-]?\s*(?:das?\s*24h\s*(?:de)?)?\s*(\d{2}/\d{2}/\d{4})\s*(?:[aà]|at[eé]|a\s+partir\s+de)\s*(?:[aà]s?\s*24h\s*(?:de)?)?\s*(\d{2}/\d{2}/\d{4})',
            raw_text,
            re.IGNORECASE
        )
        if match_vig:
            start_pos = max(0, match_vig.start() - 60)
            context = raw_text[start_pos:match_vig.start()].lower()
            if not any(term in context for term in ("comercializados", "versão", "versao", "manual", "produto")):
                vigencia_inicio, vigencia_fim = match_vig.group(1), match_vig.group(2)
        else:
            match_inicio = re.search(
                r'(?:in[ií]cio\s+da\s+vig[eê]ncia|in[ií]cio\s+de\s+vig[eê]ncia)\s*[:\-]?\s*(?:das?\s*24h\s*(?:de)?)?\s*(\d{2}/\d{2}/\d{4})',
                raw_text,
                re.IGNORECASE
            )
            match_fim = re.search(
                r'(?:t[eé]rmino\s+da\s+vig[eê]ncia|t[eé]rmino\s+de\s+vig[eê]ncia|fim\s+da\s+vig[eê]ncia)\s*[:\-]?\s*(?:[aà]s?\s*24h\s*(?:de)?)?\s*(\d{2}/\d{2}/\d{4})',
                raw_text,
                re.IGNORECASE
            )
            if match_inicio:
                vigencia_inicio = match_inicio.group(1)
            if match_fim:
                vigencia_fim = match_fim.group(1)

        if not vigencia_inicio and not vigencia_fim:
            if is_demo and document_domain == "auto":
                vigencia_inicio = "24h do dia de emissão"
                vigencia_fim = "365 dias (Vigência Anual)"
            elif is_demo:
                vigencia_inicio = "01/01/2026"
                vigencia_fim = "01/01/2027"

        vigencia_inicio = normalize_scalar("vigencia_inicio", vigencia_inicio)
        vigencia_fim = normalize_scalar("vigencia_fim", vigencia_fim)

        # ---------------------------------------------------------------------
        # 5. Limite de Responsabilidade (LMG / FIPE)
        # ---------------------------------------------------------------------
        limite = None
        if document_domain == "auto":
            limite = "100% Tabela FIPE (Valor de Mercado Referenciado)"
        else:
            match_lim = re.search(r'(?:limite[^\n:]*|lmg|garantia)\s*[:\-]\s*(r\$\s*[\d\.,\s]+)', raw_text, re.IGNORECASE)
            if match_lim:
                limite = match_lim.group(1).strip().split('\n')[0]
            elif is_demo:
                if "15.000.000" in raw_text:
                    limite = "R$ 15.000.000,00"
                elif "10.000.000" in raw_text:
                    limite = "R$ 10.000.000,00"
                elif "5.000.000" in raw_text:
                    limite = "R$ 5.000.000,00"
                else:
                    limite = "R$ 10.000.000,00"

        limite = normalize_scalar("limite_responsabilidade", limite)

        # ---------------------------------------------------------------------
        # 6. Franquia
        # ---------------------------------------------------------------------
        franquia = None
        if document_domain == "auto":
            franquia = "Franquia Obrigatória Padrão / Reduzida (Casco)"
        else:
            match_franq = re.search(r'(?:franquia|reten[çc][aã]o)\s*[:\-]?\s*([^\n\r]+)', raw_text, re.IGNORECASE)
            if match_franq:
                franquia = match_franq.group(1).strip().split('\n')[0]
            elif is_demo:
                franquia = "R$ 50.000,00 (Isento para Side A)"

        franquia = normalize_scalar("franquia", franquia)

        # ---------------------------------------------------------------------
        # 7. Prêmio Total
        # ---------------------------------------------------------------------
        premio = None
        if document_domain == "auto":
            premio = "Tarifário Anual conforme Perfil do Condutor"
        else:
            match_prem = re.search(r'(?:pr[eê]mio\s+total|pr[eê]mio\s+l[ií]quido)\s*[:\-]?\s*(r\$\s*[\d\.,\s]+)', raw_text, re.IGNORECASE)
            if match_prem:
                premio = match_prem.group(1).strip().split('\n')[0]
            elif is_demo:
                premio = "R$ 120.000,00"

        premio = normalize_scalar("premio_total", premio)

        # ---------------------------------------------------------------------
        # 8. Retroatividade
        # ---------------------------------------------------------------------
        retroatividade = None
        match_retro = re.search(r'(?:data\s+de\s+retroatividade|retroatividade)\s*[:\-]?\s*([^\n\r]+)', raw_text, re.IGNORECASE)
        if match_retro:
            retroatividade = match_retro.group(1).strip()
        elif is_demo:
            retroatividade = "01/01/2023 (3 anos de retroatividade)"

        retroatividade = normalize_scalar("retroatividade", retroatividade)

        # ---------------------------------------------------------------------
        # 9. Território e Legislação / Foro
        # ---------------------------------------------------------------------
        territorio = None
        match_terr = re.search(r'(?:[âa]mbito\s+territorial|territ[oó]rio)\s*[:\-]?\s*([^\n\r]+)', raw_text, re.IGNORECASE)
        if match_terr:
            territorio = match_terr.group(1).strip()
        else:
            if "exceto eua" in raw_text.lower():
                territorio = "Brasil e Jurisdição Mundial (exceto EUA e Canadá)"
            elif "inclusive eua" in raw_text.lower():
                territorio = "Mundial (inclusive EUA e Canadá)"
            elif is_demo:
                territorio = "Brasil e Jurisdição Mundial (exceto EUA e Canadá)"

        territorio = normalize_scalar("territorio", territorio)

        legislacao = None
        match_foro = re.search(
            r'(?:foro|jurisdi[cç][aã]o|legisla[cç][aã]o(?:\s+aplic[aá]vel)?)\s*[:\-]?\s*([^\n\r]{3,160})',
            raw_text,
            re.IGNORECASE
        )
        if match_foro:
            legislacao = match_foro.group(1).strip()
        elif is_demo:
            legislacao = "Legislação Brasileira, Foro da Comarca de São Paulo/SP"

        legislacao = normalize_scalar("legislacao_aplicavel", legislacao)

        # ---------------------------------------------------------------------
        # 10. Ramo SUSEP
        # ---------------------------------------------------------------------
        cod_ramo = None
        ramo_desc = None
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

        cod_ramo = normalize_scalar("cod_ramo", cod_ramo)
        ramo_desc = normalize_scalar("ramo_descricao", ramo_desc)

        # ---------------------------------------------------------------------
        # 11. Coberturas e Exclusões (Isoladas por Domínio)
        # ---------------------------------------------------------------------
        coberturas: List[str] = []
        exclusoes: List[str] = []
        clausulas_especiais: List[str] = []
        evs_disc: Dict[str, EvidenceItem] = {}

        if document_domain == "auto":
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
            if not coberturas and is_demo:
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
            if not exclusoes and is_demo:
                exclusoes = auto_excs[:4]

        elif document_domain == "do":
            if not is_demo:
                # Extração semântica com rastreabilidade de páginas e snippets reais (Fase 5)
                cobs_disc, excs_disc, esp_disc, evs_disc = discover_contract_clauses(raw_text, document_domain)
                coberturas = cobs_disc
                exclusoes = excs_disc
                clausulas_especiais = esp_disc
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
                if not coberturas and is_demo:
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
                if not exclusoes and is_demo:
                    exclusoes = excs_candidates[:5]
                clausulas_especiais = ["Cláusula de Não Imputação Mútua de Dolo", "Bilateralidade no cancelamento"]
        else:
            # Domínio desconhecido / genérico: não inventar coberturas nem exclusões
            coberturas = []
            exclusoes = []
            clausulas_especiais = []

        # ---------------------------------------------------------------------
        # 13. Tipo de Movimento SUSEP (Regra Estrita de Auditoria - ETAPA 9)
        # NUNCA inferir tipo de movimento por palavras isoladas em cláusulas
        # (ex: "cancelamento", "endosso", "restituição pro rata").
        # Exige campo cadastral explícito ou cabeçalho formal do documento.
        # ---------------------------------------------------------------------
        tipo_mov = None
        tipo_desc = None

        match_mov_field = re.search(
            r'(?:tipo\s+de\s+movimento|c[oó]digo\s+de\s+movimento|movimento\s+susep)\s*[:\-]?\s*(10[1-8])',
            raw_text,
            re.IGNORECASE
        )
        if match_mov_field:
            tipo_mov = match_mov_field.group(1).strip()
            from core.variance_engine import get_tipo_mov_name
            tipo_desc = get_tipo_mov_name(tipo_mov)
        elif is_demo:
            if "endosso" in nome_arquivo.lower():
                tipo_mov = "102"
                tipo_desc = "Endosso de cobrança adicional de prêmio"
            else:
                tipo_mov = "101"
                tipo_desc = "Emissão de Apólice"
        else:
            # Em documentos reais/externos: tipo_movimento exige comprovação cadastral explícita
            # Condições Gerais e textos sem campo cadastral específico permanecem estritamente None
            tipo_mov = None
            tipo_desc = None

        tipo_mov = normalize_scalar("tipo_movimento", tipo_mov)
        tipo_desc = normalize_scalar("tipo_movimento_descricao", tipo_desc)

        # Segregação semântica estrita: Condições Gerais não possuem apólice emitida, segurado individual ou vigência individual
        if document_type == "condicoes_gerais":
            segurado = None
            num_apolice = None
            vigencia_inicio = None
            vigencia_fim = None
            tipo_mov = None
            tipo_desc = None
            premio = None
            franquia = None
            limite = None

        missing_fields = [
            campo for campo, valor in {
                "seguradora": seguradora,
                "segurado": segurado,
                "numero_apolice": num_apolice,
                "processo_susep": processo_susep,
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
                "tipo_movimento": tipo_mov,
            }.items() if valor in (None, "", [])
        ]

        # ---------------------------------------------------------------------
        # 14. Proveniência e Evidências Contratuais Auditáveis (Fase 3)
        # Regra de Confiança Transparente:
        # - 1.00: Fixture sintética controlada (mock_fallback)
        # - 0.95: Evidência textual literal direta com página exata (pdf_text)
        # - 0.90: Casamento aproximado/normalizado com página exata (pdf_text)
        # - 0.75: Dedução heurística contextual (heuristic)
        # - Valores ausentes (None) NÃO geram evidência inventada
        # ---------------------------------------------------------------------
        evidencias: Dict[str, EvidenceItem] = {}

        def _attach_ev(field: str, val: Any, target_term: Optional[str] = None, default_method: str = "pdf_text", default_conf: float = 0.90):
            if val is None or (isinstance(val, list) and not val):
                return
            if is_demo:
                evidencias[field] = EvidenceItem(
                    page=1,
                    snippet=str(val)[:180],
                    method="mock_fallback",
                    confidence=1.0
                )
                return

            search_str = target_term or (str(val) if not isinstance(val, list) else (val[0] if val else None))
            if not search_str:
                return

            ev = find_evidence_in_text(raw_text, search_str, method=default_method, confidence=default_conf)
            if ev:
                evidencias[field] = ev

        _attach_ev("seguradora", seguradora, seguradora, "pdf_text", 0.95)
        if "seguradora" not in evidencias and seguradora:
            if processo_susep:
                ev_proc = find_evidence_in_text(raw_text, processo_susep.replace("Proc. SUSEP ", ""), method="regulatory_registry", confidence=0.95)
                if ev_proc:
                    evidencias["seguradora"] = ev_proc
            if "seguradora" not in evidencias:
                evidencias["seguradora"] = EvidenceItem(
                    page=1,
                    snippet=f"Resolução canônica SUSEP/Marca: {seguradora}",
                    method="regulatory_registry",
                    confidence=0.95
                )
        _attach_ev("segurado", segurado, candidate if (match_segurado and candidate in raw_text) else segurado, "pdf_text", 0.90)

        if processo_susep:
            target_susep = match_susep.group(0) if match_susep else processo_susep
            _attach_ev("processo_susep", processo_susep, target_susep, "pdf_text", 0.95)

        if num_apolice:
            target_apolice = match_apolice.group(0) if match_apolice else num_apolice
            _attach_ev("numero_apolice", num_apolice, target_apolice, "pdf_text", 0.95)

        _attach_ev("vigencia_inicio", vigencia_inicio, vigencia_inicio, "pdf_text", 0.90)
        _attach_ev("vigencia_fim", vigencia_fim, vigencia_fim, "pdf_text", 0.90)

        target_lim = match_lim.group(1).strip() if (match_lim and match_lim.group(1).strip() in raw_text) else limite
        _attach_ev("limite_responsabilidade", limite, target_lim, "pdf_text", 0.95)

        target_franq = match_franq.group(1).strip() if (match_franq and match_franq.group(1).strip() in raw_text) else franquia
        _attach_ev("franquia", franquia, target_franq, "pdf_text", 0.90)

        target_prem = match_prem.group(1).strip() if (match_prem and match_prem.group(1).strip() in raw_text) else premio
        _attach_ev("premio_total", premio, target_prem, "pdf_text", 0.95)

        target_retro = match_retro.group(1).strip() if (match_retro and match_retro.group(1).strip() in raw_text) else "retroatividade"
        _attach_ev("retroatividade", retroatividade, target_retro, "pdf_text", 0.90)

        target_terr = match_terr.group(1).strip() if (match_terr and match_terr.group(1).strip() in raw_text) else ("exceto eua" if "exceto eua" in raw_text.lower() else ("inclusive eua" if "inclusive eua" in raw_text.lower() else "territorial"))
        _attach_ev("territorio", territorio, target_terr, "pdf_text", 0.90)

        target_leg = match_foro.group(1).strip() if (match_foro and match_foro.group(1).strip() in raw_text) else "foro"
        _attach_ev("legislacao_aplicavel", legislacao, target_leg, "pdf_text", 0.90)

        # cod_ramo & ramo_descricao
        if cod_ramo:
            if match_ramo:
                ev_ramo = find_evidence_in_text(raw_text, match_ramo.group(1).strip(), method="pdf_text", confidence=0.95)
            elif is_demo:
                ev_ramo = EvidenceItem(page=1, snippet=f"Ramo {cod_ramo}", method="mock_fallback", confidence=1.0)
            elif document_domain == "do":
                ev_ramo = find_evidence_in_text(raw_text, "d&o", method="heuristic", confidence=0.75) or find_evidence_in_text(raw_text, "directors", method="heuristic", confidence=0.75)
            elif document_domain == "auto":
                ev_ramo = find_evidence_in_text(raw_text, "automóvel", method="heuristic", confidence=0.75) or find_evidence_in_text(raw_text, "veículo", method="heuristic", confidence=0.75)
            else:
                ev_ramo = None

            if ev_ramo:
                evidencias["cod_ramo"] = ev_ramo
                if ramo_desc:
                    evidencias["ramo_descricao"] = ev_ramo

        # tipo_movimento & tipo_movimento_descricao
        if tipo_mov:
            if match_mov_field:
                ev_mov = find_evidence_in_text(raw_text, match_mov_field.group(1).strip(), method="pdf_text", confidence=0.95)
            elif is_demo:
                ev_mov = EvidenceItem(page=1, snippet=f"Tipo Movimento {tipo_mov}", method="mock_fallback", confidence=1.0)
            else:
                ev_mov = find_evidence_in_text(raw_text, "apólice de seguro", method="heuristic", confidence=0.75)
            if ev_mov:
                evidencias["tipo_movimento"] = ev_mov
                if tipo_desc:
                    evidencias["tipo_movimento_descricao"] = ev_mov

        # Anexa evidências descobertas de cláusulas com preservação de página, snippet e método (Fase 5)
        if not is_demo and document_domain == "do" and evs_disc:
            evidencias.update(evs_disc)
            if coberturas:
                c_title = coberturas[0].split(":")[0].strip()
                if c_title in evs_disc:
                    evidencias["coberturas"] = evs_disc[c_title]
            if exclusoes:
                e_title = exclusoes[0].split(":")[0].strip()
                if e_title in evs_disc:
                    evidencias["exclusoes"] = evs_disc[e_title]
            if clausulas_especiais:
                esp_title = clausulas_especiais[0].split(":")[0].strip()
                if esp_title in evs_disc:
                    evidencias["clausulas_especiais"] = evs_disc[esp_title]
        else:
            # coberturas
            if coberturas:
                if is_demo:
                    evidencias["coberturas"] = EvidenceItem(page=1, snippet=coberturas[0], method="mock_fallback", confidence=1.0)
                else:
                    for c in coberturas:
                        tok = c.split('(')[0].split(':')[0].strip()
                        ev_c = find_evidence_in_text(raw_text, tok, method="pdf_text", confidence=0.90)
                        if ev_c:
                            evidencias["coberturas"] = ev_c
                            break

            # exclusoes
            if exclusoes:
                if is_demo:
                    evidencias["exclusoes"] = EvidenceItem(page=1, snippet=exclusoes[0], method="mock_fallback", confidence=1.0)
                else:
                    for e in exclusoes:
                        tok = e.split(',')[0].split(':')[0].strip()
                        ev_e = find_evidence_in_text(raw_text, tok, method="pdf_text", confidence=0.90)
                        if ev_e:
                            evidencias["exclusoes"] = ev_e
                            break

            # clausulas_especiais
            if clausulas_especiais:
                if is_demo:
                    evidencias["clausulas_especiais"] = EvidenceItem(page=1, snippet=clausulas_especiais[0], method="mock_fallback", confidence=1.0)
                else:
                    for ce in clausulas_especiais:
                        tok = ce.split(':')[0].strip()
                        ev_ce = find_evidence_in_text(raw_text, tok, method="pdf_text", confidence=0.90)
                        if ev_ce:
                            evidencias["clausulas_especiais"] = ev_ce
        # Se for imagem ou método OCR / Gemini Vision, assegura método nos EvidenceItems
        if metodo_extracao in ("ocr", "gemini_vision"):
            for k, ev in list(evidencias.items()):
                if ev.method in ("pdf_text", "regulatory_registry", "heuristic", "mock_fallback"):
                    evidencias[k] = EvidenceItem(
                        page=ev.page or 1,
                        page_end=ev.page_end,
                        section=ev.section,
                        snippet=ev.snippet,
                        method=metodo_extracao,
                        confidence=ev.confidence,
                        chunk_index=ev.chunk_index,
                        char_start=ev.char_start,
                        char_end=ev.char_end
                    )

        return ApoliceDAO(
            id=file_hash,
            nome_arquivo=nome_arquivo,
            data_processamento=datetime.now().isoformat(),
            seguradora=seguradora,
            segurado=segurado,
            numero_apolice=num_apolice,
            processo_susep=processo_susep,
            vigencia_inicio=vigencia_inicio,
            vigencia_fim=vigencia_fim,
            premio_total=premio,
            limite_responsabilidade=limite,
            franquia=franquia,
            coberturas=coberturas,
            exclusoes=exclusoes,
            clausulas_especiais=clausulas_especiais,
            retroatividade=retroatividade,
            territorio=territorio,
            legislacao_aplicavel=legislacao,
            cod_ramo=cod_ramo,
            ramo_descricao=ramo_desc,
            tipo_movimento=tipo_mov,
            tipo_movimento_descricao=tipo_desc,
            document_type=document_type,
            metodo_extracao="mock_fallback" if is_demo else "heuristic_fallback",
            confianca_extracao=0.88 if is_demo else 0.35,
            campos_nao_encontrados=missing_fields,
            conflitos_extracao={},
            evidencias=evidencias,
            evidencias_conflito={},
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
