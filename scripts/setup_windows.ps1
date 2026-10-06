<#
.SYNOPSIS
    scripts/setup_windows.ps1 — Script de Instalação e Configuração Reproduzível no Windows 11.
.DESCRIPTION
    Configura o ambiente virtual Python, instala as dependências auditadas de runtime/dev,
    detecta a instalação do Tesseract OCR no Windows e executa o diagnóstico de validação.
.NOTES
    Governança:
    - NÃO baixa executáveis arbitrários sem confirmação explícita;
    - NÃO altera variáveis de ambiente globais silenciosamente;
    - NÃO sobrescreve configurações ou bancos existentes do usuário;
    - NÃO armazena nem expõe chaves de API.
#>

[CmdletBinding()]
param (
    [string]$VenvPath = ".venv",
    [switch]$InstallDev = $false
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "CONFIGURAÇÃO DE AMBIENTE WINDOWS 11 — INSURMINDS APÓLICE ANALYZER" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan

# 1. Verificação do Interpretador Python
Write-Host "[1/6] Verificando interpretador Python..." -ForegroundColor Yellow

$PythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py -3"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} else {
    Write-Host "✗ ERRO CRÍTICO: Python não foi encontrado no PATH do Windows." -ForegroundColor Red
    Write-Host "  Instale o Python 3.10 ou superior a partir de: https://www.python.org/downloads/windows/" -ForegroundColor Yellow
    Write-Host "  Certifique-se de marcar a opção 'Add Python to PATH' no instalador oficial." -ForegroundColor Yellow
    Exit 1
}

$PyVerOutput = Invoke-Expression "$PythonCmd -c ""import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"""
$PyMajor = [int](Invoke-Expression "$PythonCmd -c ""import sys; print(sys.version_info.major)""")
$PyMinor = [int](Invoke-Expression "$PythonCmd -c ""import sys; print(sys.version_info.minor)""")

if ($PyMajor -lt 3 -or ($PyMajor -eq 3 -and $PyMinor -lt 10)) {
    Write-Host "✗ ERRO: Python $PyVerOutput detectado. O projeto exige Python >= 3.10." -ForegroundColor Red
    Exit 1
}
Write-Host "  ✓ Python compatível localizado: Python $PyVerOutput" -ForegroundColor Green

# 2. Criação / Verificação do Ambiente Virtual
Write-Host "`n[2/6] Configurando ambiente virtual ($VenvPath)..." -ForegroundColor Yellow

if (-not (Test-Path $VenvPath)) {
    Write-Host "  Criando novo venv em '$VenvPath'..." -ForegroundColor Gray
    Invoke-Expression "$PythonCmd -m venv $VenvPath"
    Write-Host "  ✓ Ambiente virtual criado com sucesso." -ForegroundColor Green
} else {
    Write-Host "  ✓ Ambiente virtual existente reaproveitado em '$VenvPath'." -ForegroundColor Green
}

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$VenvPip = Join-Path $VenvPath "Scripts\pip.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "✗ ERRO: O executável '$VenvPython' não foi encontrado." -ForegroundColor Red
    Exit 1
}

# 3. Atualização de Pip e Instalação de Requirements
Write-Host "`n[3/6] Instalando dependências oficiais via pip..." -ForegroundColor Yellow
& $VenvPython -m pip install --quiet --upgrade pip setuptools wheel

$ReqFile = if ($InstallDev) { "requirements-dev.txt" } else { "requirements.txt" }
Write-Host "  Instalando pacotes de '$ReqFile'..." -ForegroundColor Gray
& $VenvPip install --quiet -r $ReqFile
Write-Host "  ✓ Dependências Python instaladas com sucesso." -ForegroundColor Green

# 4. Detecção do Motor Tesseract OCR no Windows
Write-Host "`n[4/6] Verificando dependências de sistema para OCR (Tesseract)..." -ForegroundColor Yellow

$TesseractBinary = $null
if (Get-Command tesseract -ErrorAction SilentlyContinue) {
    $TesseractBinary = (Get-Command tesseract).Source
} else {
    $StandardPaths = @(
        "C:\Program Files\Tesseract-OCR\tesseract.exe",
        "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "$env:LOCALAPPDATA\Programs\Tesseract-OCR\tesseract.exe"
    )
    foreach ($PathCandidate in $StandardPaths) {
        if (Test-Path $PathCandidate) {
            $TesseractBinary = $PathCandidate
            break
        }
    }
}

if ($TesseractBinary) {
    $TessVer = & $TesseractBinary --version 2>&1 | Select-Object -First 1
    Write-Host "  ✓ Tesseract detectado: $TessVer" -ForegroundColor Green
    Write-Host "    Caminho: $TesseractBinary" -ForegroundColor Gray

    # Configuração temporária de sessão para a execução
    $env:TESSERACT_CMD = $TesseractBinary
    $TessdataCandidate = Join-Path (Split-Path -Parent $TesseractBinary) "tessdata"
    if (Test-Path $TessdataCandidate) {
        $env:TESSDATA_PREFIX = $TessdataCandidate
        $HasPor = Test-Path (Join-Path $TessdataCandidate "por.traineddata")
        if ($HasPor) {
            Write-Host "    ✓ Suporte ao Português (por.traineddata) localizado." -ForegroundColor Green
        } else {
            Write-Host "    ⚠ Modelo 'por.traineddata' não encontrado em tessdata (usará 'eng')." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "  ℹ Tesseract CLI não encontrado nos caminhos padrão do Windows." -ForegroundColor Yellow
    Write-Host "    O PyMuPDF tentará OCR via biblioteca, mas para suporte completo recomendamos:" -ForegroundColor Gray
    Write-Host "    1. Baixar o instalador oficial: https://github.com/UB-Mannheim/tesseract/wiki" -ForegroundColor Cyan
    Write-Host "    2. No assistente de instalação, marcar 'Additional language data (download)' -> 'Portuguese'" -ForegroundColor Cyan
    Write-Host "    3. Caso instalado em local personalizado, defina no terminal:" -ForegroundColor Gray
    Write-Host "       `$env:TESSERACT_CMD = 'C:\caminho\para\tesseract.exe'" -ForegroundColor Gray
}

# 5. Execução do Diagnóstico de Validação de Ambiente
Write-Host "`n[5/6] Executando diagnóstico oficial com scripts/validate_environment.py..." -ForegroundColor Yellow
& $VenvPython scripts/validate_environment.py

# 6. Orientações de Execução e Chave Gemini
Write-Host "`n[6/6] Orientações finais de operação:" -ForegroundColor Yellow
Write-Host "  • Para ativar o ambiente virtual no PowerShell:" -ForegroundColor White
Write-Host "      .\$VenvPath\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "    (Caso ocorra restrição de scripts: Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass)" -ForegroundColor Gray
Write-Host "  • Para configurar o Google Gemini (opcional — fallback determinístico opera sem chave):" -ForegroundColor White
Write-Host "      `$env:GOOGLE_API_KEY=""sua_chave_aqui""" -ForegroundColor Cyan
Write-Host "      ou crie um arquivo .env na raiz do projeto com GOOGLE_API_KEY=sua_chave" -ForegroundColor Gray
Write-Host "  • Para iniciar a interface gráfica do InsurMinds:" -ForegroundColor White
Write-Host "      streamlit run app.py" -ForegroundColor Cyan

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "✓ SETUP DO WINDOWS 11 CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
