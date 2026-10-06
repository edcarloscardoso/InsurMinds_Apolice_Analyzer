================================================================================
INSURMINDS APÓLICE ANALYZER — PROTOCOLO DE VALIDAÇÃO FÍSICA WINDOWS 11
================================================================================

1. Pré-requisito: Windows 11 64-bit.
2. Instalar Tesseract OCR 64-bit com português (tesseract-ocr-w64-setup com modelo 'por').
3. Abrir PowerShell (como Administrador ou com permissão de execução de scripts).
4. Executar o script de provisionamento:
   .\scripts\setup_windows.ps1
5. Validar o ambiente e resolução de caminhos:
   .\.venv\Scripts\python.exe scripts\validate_environment.py
6. Executar a suíte completa de testes automatizados (182 testes esperados):
   .\.venv\Scripts\python.exe -m pytest tests\ -q
7. Iniciar a aplicação web:
   .\.venv\Scripts\python.exe -m streamlit run app.py
8. Validar manualmente o fluxo funcional na interface:
   - Upload de PDF digital (ex: data\sample_policies\apolice_do_allianz.pdf);
   - Upload de PDF escaneado ou imagem (PNG, JPG/JPEG);
   - Comparação analítica entre duas apólices (ex: Sompo v1.2 x Sompo v1.5 ou Allianz x Chubb);
   - Abertura do drawer de evidência contratual (verificar página e snippet);
   - Geração e leitura do Parecer Executivo Narrativo;
   - Exportação do relatório em Markdown e JSON estruturado.
9. Registrar screenshots/evidências do teste para o relatório final.

================================================================================
