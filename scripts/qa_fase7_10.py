"""Script de QA Visual Global Automatizado — FASE 7.10 (Integração Visual e Consistência Global).
Executa o fluxo completo do usuário através de todas as telas integradas:
Workspace → Nova Análise → Comparação → Detalhe → Evidência → Relatório → Biblioteca → Assistente.
Testa dados reais (Sompo e Chubb) e valida resoluções 1440x900, 1366x768 e 1024x768 via Chrome CDP.
"""
import asyncio
import base64
import json
import os
import subprocess
import time
import requests
import websockets

ARTIFACT_DIR = os.environ.get("QA_ARTIFACT_DIR", str(Path(__file__).resolve().parent.parent / "docs" / "captura_telas"))


async def cdp_command(ws, method, params=None, msg_id=1):
    msg = {"id": msg_id, "method": method, "params": params or {}}
    await ws.send(json.dumps(msg))
    while True:
        resp = await ws.recv()
        data = json.loads(resp)
        if data.get("id") == msg_id:
            return data


async def save_screenshot(ws, filename: str):
    shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
    filepath = os.path.join(ARTIFACT_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(base64.b64decode(shot_res["result"]["data"]))
    print(f"Screenshot salvo: {filepath}")
    return filepath


async def run_global_qa():
    subprocess.run("lsof -ti:9222 | xargs -r kill -9", shell=True)
    chrome_proc = subprocess.Popen([
        "/usr/bin/google-chrome",
        "--headless=new",
        "--remote-debugging-port=9222",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "about:blank"
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)

    try:
        targets = requests.get("http://localhost:9222/json").json()
        page_target = [t for t in targets if t.get("type") == "page"][0]
        ws_url = page_target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            await cdp_command(ws, "Page.enable")
            await cdp_command(ws, "Runtime.enable")

            # -----------------------------------------------------------------
            # 1. WORKSPACE (1440x900)
            # -----------------------------------------------------------------
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1440,
                "height": 900,
                "deviceScaleFactor": 1,
                "mobile": False
            })

            print("\n[QA 1] Acessando Workspace / Início...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=inicio"})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_10_01_workspace_1440.png")

            # -----------------------------------------------------------------
            # 2. NOVA ANÁLISE (1440x900)
            # -----------------------------------------------------------------
            print("[QA 2] Acessando Nova Análise...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=nova_analise"})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_10_02_nova_analise_1440.png")

            # -----------------------------------------------------------------
            # 3. COMPARAÇÃO (1440x900)
            # -----------------------------------------------------------------
            print("[QA 3] Acessando Comparação...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=comparacoes"})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_10_03_comparacao_1440.png")

            # -----------------------------------------------------------------
            # 4. DETALHE DA DIFERENÇA (1440x900)
            # -----------------------------------------------------------------
            print("[QA 4] Navegando para Detalhe da Diferença...")
            click_audit = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && b.innerText.includes('Auditar Detalhe'));
                if (btn) {
                    btn.click();
                    return "Clicado auditar detalhe";
                }
                return "Não encontrado";
            })()
            """
            res_audit = await cdp_command(ws, "Runtime.evaluate", {"expression": click_audit, "returnByValue": True})
            print("Clique detalhe:", res_audit.get("result", {}).get("value"))
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_10_04_detalhe_1440.png")

            # -----------------------------------------------------------------
            # 5. EVIDÊNCIA LITERAL EXPANDIDA (1440x900)
            # -----------------------------------------------------------------
            print("[QA 5] Expandindo evidência documental literal...")
            click_ev_exp = """
            (() => {
                const details = Array.from(document.querySelectorAll('details'));
                if (details.length > 0) {
                    details[0].open = true;
                    return "Expander aberto";
                }
                return "Sem expander";
            })()
            """
            await cdp_command(ws, "Runtime.evaluate", {"expression": click_ev_exp, "returnByValue": True})
            await asyncio.sleep(2)
            await save_screenshot(ws, "fase7_10_05_evidencia_1440.png")

            # -----------------------------------------------------------------
            # 6. VOLTAR À COMPARAÇÃO (1440x900)
            # -----------------------------------------------------------------
            print("[QA 6] Clicando em 'Voltar à Comparação'...")
            click_back = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && b.innerText.includes('Voltar à Comparação'));
                if (btn) {
                    btn.click();
                    return "Clicado voltar";
                }
                return "Não encontrado";
            })()
            """
            await cdp_command(ws, "Runtime.evaluate", {"expression": click_back, "returnByValue": True})
            await asyncio.sleep(3)
            await save_screenshot(ws, "fase7_10_06_back_to_compare_1440.png")

            # -----------------------------------------------------------------
            # 7. RELATÓRIO EXECUTIVO (1440x900)
            # -----------------------------------------------------------------
            print("[QA 7] Acessando Relatórios...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=relatorios"})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_10_07_relatorio_1440.png")

            # -----------------------------------------------------------------
            # 8. BIBLIOTECA DE DOCUMENTOS (1440x900)
            # -----------------------------------------------------------------
            print("[QA 8] Acessando Documentos / Biblioteca...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=documentos"})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_10_08_biblioteca_1440.png")

            # -----------------------------------------------------------------
            # 9. ASSISTENTE CONTEXTUAL ATIVO (1440x900)
            # -----------------------------------------------------------------
            print("[QA 9] Abrindo Assistente Contextual...")
            click_asst = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && (b.innerText.includes('Assistente') || b.innerText.includes('🧠')));
                if (btn) {
                    btn.click();
                    return "Clicado assistente";
                }
                return "Não encontrado";
            })()
            """
            await cdp_command(ws, "Runtime.evaluate", {"expression": click_asst, "returnByValue": True})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_10_09_assistente_1440.png")

            # -----------------------------------------------------------------
            # 10. RESPONSIVIDADE 1366x768 (Notebook Corporativo)
            # -----------------------------------------------------------------
            print("[QA 10] Testando 1366x768...")
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(2)
            await save_screenshot(ws, "fase7_10_10_responsive_1366.png")

            # -----------------------------------------------------------------
            # 11. RESPONSIVIDADE 1024x768 (Compacto)
            # -----------------------------------------------------------------
            print("[QA 11] Testando 1024x768...")
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1024,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(2)
            await save_screenshot(ws, "fase7_10_11_responsive_1024.png")

    finally:
        chrome_proc.terminate()
        print("\nQA Visual Global Fase 7.10 concluído!")


if __name__ == "__main__":
    asyncio.run(run_global_qa())
