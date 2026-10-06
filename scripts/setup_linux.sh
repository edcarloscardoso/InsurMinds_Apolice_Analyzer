#!/usr/bin/env bash
# scripts/setup_linux.sh — Script de Inicialização e Instalação Reproduzível no Linux.
# Configura o ambiente virtual, instala as dependências auditadas e valida o sistema.
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
RESET="\033[0m"

echo -e "================================================================================"
echo -e "${BOLD}INICIALIZAÇÃO DO AMBIENTE LINUX — INSURMINDS APÓLICE ANALYZER${RESET}"
echo -e "================================================================================"

# 1. Verificação do interpretador Python
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
    echo -e "${RED}✗ Erro: '$PYTHON_BIN' não foi encontrado no PATH.${RESET}"
    exit 1
fi

PY_VER=$($PYTHON_BIN -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON_BIN -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MINOR" -lt 10 ]; then
    echo -e "${RED}✗ Versão de Python incompatível: $PY_VER detectada. O projeto requer Python >= 3.10.${RESET}"
    exit 1
fi
echo -e "[1/5] Interpretador Python: ${GREEN}✓ $PYTHON_BIN (v$PY_VER >= 3.10)${RESET}"

# 2. Configuração do Ambiente Virtual
VENV_DIR="${1:-.venv}"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "[2/5] Criando ambiente virtual em '${VENV_DIR}'..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    echo -e "      ${GREEN}✓ Ambiente virtual criado com sucesso.${RESET}"
else
    echo -e "[2/5] Ambiente virtual já existente em '${VENV_DIR}'. ${GREEN}✓${RESET}"
fi

VENV_PYTHON="${VENV_DIR}/bin/python3"
VENV_PIP="${VENV_DIR}/bin/pip"

# 3. Atualização de Pip e Instalação dos Requirements
echo -e "[3/5] Instalando dependências de 'requirements.txt'..."
"$VENV_PIP" install --quiet --upgrade pip setuptools wheel
"$VENV_PIP" install --quiet -r requirements.txt
echo -e "      ${GREEN}✓ Dependências instaladas com sucesso.${RESET}"

# 4. Verificação de Tesseract OCR no Sistema
echo -e "[4/5] Verificando dependências de sistema para OCR..."
if command -v tesseract &>/dev/null; then
    TESS_VER=$(tesseract --version 2>&1 | head -n 1)
    echo -e "      ${GREEN}✓ Tesseract CLI encontrado: ${TESS_VER}${RESET}"
else
    echo -e "      ${YELLOW}ℹ Tesseract CLI não encontrado no PATH.${RESET}"
    echo -e "      ${BOLD}O OCR nativo funcionará via PyMuPDF (libtesseract5), mas para suporte CLI completo instale:${RESET}"
    echo -e "        - openSUSE:        sudo zypper install tesseract-ocr tesseract-ocr-traineddata-por"
    echo -e "        - Ubuntu / Debian: sudo apt-get install tesseract-ocr tesseract-ocr-por"
    echo -e "        - Fedora:          sudo dnf install tesseract tesseract-langpack-por"
    echo -e "        - Arch Linux:      sudo pacman -S tesseract tesseract-data-por"
fi

# 5. Validação Integral do Ambiente
echo -e "[5/5] Executando diagnóstico com 'scripts/validate_environment.py'..."
"$VENV_PYTHON" scripts/validate_environment.py

echo -e "================================================================================"
echo -e "${GREEN}${BOLD}✓ AMBIENTE LINUX CONFIGURADO COM SUCESSO!${RESET}"
echo -e "Para ativar o ambiente e iniciar a aplicação:"
echo -e "  source ${VENV_DIR}/bin/activate"
echo -e "  streamlit run app.py"
echo -e "================================================================================"
