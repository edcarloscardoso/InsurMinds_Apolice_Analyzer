"""Camada de persistência relacional SQLite.
Gerencia schemas, transações ACID, consultas estritamente parametrizadas e controle de idempotência.
"""
import sqlite3
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from core.config import DB_PATH
from core.schemas import ApoliceDAO, ComparisonResult

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gerenciador centralizado de conexões e operações no SQLite."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Retorna uma conexão SQLite com suporte a linhas como dicionários."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Inicializa as tabelas e índices relacionais caso não existam."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de Apólices Ingeridas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS apolices (
                    id TEXT PRIMARY KEY,
                    nome_arquivo TEXT NOT NULL,
                    data_processamento TEXT NOT NULL,
                    segurado TEXT,
                    seguradora TEXT,
                    numero_apolice TEXT,
                    vigencia_inicio TEXT,
                    vigencia_fim TEXT,
                    premio_total TEXT,
                    limite_responsabilidade TEXT,
                    franquia TEXT,
                    coberturas_json TEXT,
                    exclusoes_json TEXT,
                    clausulas_especiais_json TEXT,
                    retroatividade TEXT,
                    territorio TEXT,
                    legislacao_aplicavel TEXT,
                    cod_ramo TEXT DEFAULT '0378',
                    ramo_descricao TEXT DEFAULT 'Responsabilidade Civil D&O',
                    tipo_movimento TEXT DEFAULT '101',
                    tipo_movimento_descricao TEXT DEFAULT 'Emissão de Apólice',
                    metodo_extracao TEXT,
                    confianca_extracao REAL,
                    campos_nao_encontrados_json TEXT,
                    dados_completos_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Migração automática idempotente para bases preexistentes
            cursor.execute("PRAGMA table_info(apolices)")
            colunas_existentes = {col[1] for col in cursor.fetchall()}
            novas_colunas = [
                ("cod_ramo", "TEXT DEFAULT '0378'"),
                ("ramo_descricao", "TEXT DEFAULT 'Responsabilidade Civil D&O'"),
                ("tipo_movimento", "TEXT DEFAULT '101'"),
                ("tipo_movimento_descricao", "TEXT DEFAULT 'Emissão de Apólice'")
            ]
            for nome_col, tipo_col in novas_colunas:
                if nome_col not in colunas_existentes:
                    cursor.execute(f"ALTER TABLE apolices ADD COLUMN {nome_col} {tipo_col}")

            # Tabela de Comparações e Pareceres
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS comparacoes (
                    id TEXT PRIMARY KEY,
                    apolice_a_id TEXT NOT NULL,
                    apolice_b_id TEXT NOT NULL,
                    score_similaridade REAL NOT NULL,
                    data_comparacao TEXT NOT NULL,
                    resultado_json TEXT NOT NULL,
                    relatorio_markdown TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(apolice_a_id) REFERENCES apolices(id) ON DELETE CASCADE,
                    FOREIGN KEY(apolice_b_id) REFERENCES apolices(id) ON DELETE CASCADE
                )
            """)

            # Índices de performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apolices_seguradora ON apolices(seguradora)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apolices_segurado ON apolices(segurado)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apolices_ramo ON apolices(cod_ramo)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_apolices_tipo_mov ON apolices(tipo_movimento)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_comparacoes_pares ON comparacoes(apolice_a_id, apolice_b_id)")
            
            conn.commit()

    def save_apolice(self, dao: ApoliceDAO) -> str:
        """Salva ou atualiza uma apólice estruturada no banco (Idempotência por Hash ID)."""
        if not dao.id:
            raise ValueError("ApoliceDAO deve conter um 'id' (hash MD5) válido para persistência.")

        dados_completos = dao.model_dump_json()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO apolices (
                    id, nome_arquivo, data_processamento, segurado, seguradora, numero_apolice,
                    vigencia_inicio, vigencia_fim, premio_total, limite_responsabilidade, franquia,
                    coberturas_json, exclusoes_json, clausulas_especiais_json, retroatividade,
                    territorio, legislacao_aplicavel, cod_ramo, ramo_descricao, tipo_movimento,
                    tipo_movimento_descricao, metodo_extracao, confianca_extracao,
                    campos_nao_encontrados_json, dados_completos_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    nome_arquivo = excluded.nome_arquivo,
                    data_processamento = excluded.data_processamento,
                    segurado = excluded.segurado,
                    seguradora = excluded.seguradora,
                    numero_apolice = excluded.numero_apolice,
                    vigencia_inicio = excluded.vigencia_inicio,
                    vigencia_fim = excluded.vigencia_fim,
                    premio_total = excluded.premio_total,
                    limite_responsabilidade = excluded.limite_responsabilidade,
                    franquia = excluded.franquia,
                    coberturas_json = excluded.coberturas_json,
                    exclusoes_json = excluded.exclusoes_json,
                    clausulas_especiais_json = excluded.clausulas_especiais_json,
                    retroatividade = excluded.retroatividade,
                    territorio = excluded.territorio,
                    legislacao_aplicavel = excluded.legislacao_aplicavel,
                    cod_ramo = excluded.cod_ramo,
                    ramo_descricao = excluded.ramo_descricao,
                    tipo_movimento = excluded.tipo_movimento,
                    tipo_movimento_descricao = excluded.tipo_movimento_descricao,
                    metodo_extracao = excluded.metodo_extracao,
                    confianca_extracao = excluded.confianca_extracao,
                    campos_nao_encontrados_json = excluded.campos_nao_encontrados_json,
                    dados_completos_json = excluded.dados_completos_json
            """, (
                dao.id,
                dao.nome_arquivo,
                dao.data_processamento,
                dao.segurado,
                dao.seguradora,
                dao.numero_apolice,
                dao.vigencia_inicio,
                dao.vigencia_fim,
                dao.premio_total,
                dao.limite_responsabilidade,
                dao.franquia,
                json.dumps(dao.coberturas, ensure_ascii=False),
                json.dumps(dao.exclusoes, ensure_ascii=False),
                json.dumps(dao.clausulas_especiais, ensure_ascii=False),
                dao.retroatividade,
                dao.territorio,
                dao.legislacao_aplicavel,
                dao.cod_ramo or "0378",
                dao.ramo_descricao or "Responsabilidade Civil D&O",
                dao.tipo_movimento or "101",
                dao.tipo_movimento_descricao or "Emissão de Apólice",
                dao.metodo_extracao,
                dao.confianca_extracao,
                json.dumps(dao.campos_nao_encontrados, ensure_ascii=False),
                dados_completos
            ))
            conn.commit()
            return dao.id

    def get_apolice_by_id(self, apolice_id: str) -> Optional[ApoliceDAO]:
        """Busca e desserializa uma apólice pelo seu ID único."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT dados_completos_json FROM apolices WHERE id = ?", (apolice_id,))
            row = cursor.fetchone()
            if row:
                return ApoliceDAO.model_validate_json(row["dados_completos_json"])
            return None

    def list_apolices(self) -> List[ApoliceDAO]:
        """Lista todas as apólices cadastradas, ordenadas por data de processamento."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT dados_completos_json FROM apolices ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [ApoliceDAO.model_validate_json(row["dados_completos_json"]) for row in rows]

    def delete_apolice(self, apolice_id: str) -> bool:
        """Remove uma apólice do banco relacional."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM apolices WHERE id = ?", (apolice_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_database(self) -> None:
        """Limpa todas as apólices e comparações do banco para reiniciar testes."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM comparacoes")
            cursor.execute("DELETE FROM apolices")
            conn.commit()

    def save_comparison(self, comp: ComparisonResult, report_markdown: str = "") -> str:
        """Persiste um resultado de comparação analítica e o relatório narrativo correspondente."""
        comp_id = f"{comp.apolice_a_id}_{comp.apolice_b_id}"
        resultado_json = comp.model_dump_json()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO comparacoes (
                    id, apolice_a_id, apolice_b_id, score_similaridade,
                    data_comparacao, resultado_json, relatorio_markdown
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    score_similaridade = excluded.score_similaridade,
                    data_comparacao = excluded.data_comparacao,
                    resultado_json = excluded.resultado_json,
                    relatorio_markdown = excluded.relatorio_markdown
            """, (
                comp_id,
                comp.apolice_a_id,
                comp.apolice_b_id,
                comp.score_similaridade,
                comp.data_comparacao,
                resultado_json,
                report_markdown
            ))
            conn.commit()
            return comp_id

    def get_comparison(self, apolice_a_id: str, apolice_b_id: str) -> Optional[Dict[str, Any]]:
        """Recupera uma comparação anterior entre duas apólices."""
        comp_id_1 = f"{apolice_a_id}_{apolice_b_id}"
        comp_id_2 = f"{apolice_b_id}_{apolice_a_id}"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM comparacoes WHERE id IN (?, ?) ORDER BY created_at DESC LIMIT 1
            """, (comp_id_1, comp_id_2))
            row = cursor.fetchone()
            if row:
                return {
                    "id": row["id"],
                    "apolice_a_id": row["apolice_a_id"],
                    "apolice_b_id": row["apolice_b_id"],
                    "score_similaridade": row["score_similaridade"],
                    "data_comparacao": row["data_comparacao"],
                    "resultado": ComparisonResult.model_validate_json(row["resultado_json"]),
                    "relatorio_markdown": row["relatorio_markdown"] or ""
                }
            return None


# Instância singleton padrão para o repositório
db = DatabaseManager()
