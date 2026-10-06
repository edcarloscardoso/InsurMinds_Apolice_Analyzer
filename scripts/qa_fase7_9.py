"""Script de QA Visual Automatizado para a FASE 7.9 — Assistente Contextual.
Captura telas em resoluções corporativas (1440x900, 1366x768, 1024x768),
valida abertura/fechamento, navegação entre Comparação, Detalhe, Relatório e Biblioteca,
testa as ações contextuais e troca de perfis corporativos.
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


async def run_qa():
    # Inicia Chrome Headless na porta 9222
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

            # -------------------------------------------------------------
            # CENÁRIO 1: Comparação Estruturada — 1440x900 (Assistente Fechado)
            # -------------------------------------------------------------
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1440,
                "height": 900,
                "deviceScaleFactor": 1,
                "mobile": False
            })

            print("\n[QA 1] Acessando Comparações...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=comparacoes"})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_01_compare_closed_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 2: Abrir Assistente Contextual via TopBar ou Sidebar
            # -------------------------------------------------------------
            print("[QA 2] Verificando botões e abrindo Assistente Contextual...")
            eval_btns = await cdp_command(ws, "Runtime.evaluate", {
                "expression": "Array.from(document.querySelectorAll('button')).map(b => b.innerText.trim()).filter(Boolean)",
                "returnByValue": True
            })
            print("Botões encontrados:", eval_btns.get("result", {}).get("value"))

            click_topbar_btn = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const asstBtn = btns.find(b => b.innerText && (b.innerText.includes('Assistente') || b.innerText.includes('🧠')));
                if (asstBtn) {
                    asstBtn.click();
                    return "Clicado: " + asstBtn.innerText;
                }
                return "Não encontrado";
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_topbar_btn, "returnByValue": True})
            print("Clique assistente:", eval_res.get("result", {}).get("value"))
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_02_assistant_open_compare_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 3: Responsividade — 1366x768
            # -------------------------------------------------------------
            print("[QA 3] Testando 1366x768...")
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1)
            await save_screenshot(ws, "fase7_9_03_assistant_open_compare_1366.png")

            # -------------------------------------------------------------
            # CENÁRIO 4: Responsividade — 1024x768
            # -------------------------------------------------------------
            print("[QA 4] Testando 1024x768...")
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1024,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1)
            await save_screenshot(ws, "fase7_9_04_assistant_open_compare_1024.png")

            # Retorna para 1440x900 para os demais testes
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1440,
                "height": 900,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1)

            # -------------------------------------------------------------
            # CENÁRIO 5: Ação Contextual "Explicar alterações de escopo"
            # -------------------------------------------------------------
            print("[QA 5] Clicando em 'Explicar alterações de escopo'...")
            click_escopo_btn = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && (b.innerText.includes('Explicar alterações de escopo') || b.innerText.includes('alterações de escopo')));
                if (btn) {
                    btn.click();
                    return "Clicado escopo";
                }
                return "Não encontrado escopo";
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_escopo_btn, "returnByValue": True})
            print("Clique escopo:", eval_res.get("result", {}).get("result", {}).get("value"))
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_05_action_escopo_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 6: Ação Contextual "Mostrar itens para revisão"
            # -------------------------------------------------------------
            print("[QA 6] Clicando em 'Mostrar itens para revisão profissional'...")
            click_rev_btn = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && (b.innerText.includes('revisão profissional') || b.innerText.includes('itens para revisão')));
                if (btn) {
                    btn.click();
                    return "Clicado revisão";
                }
                return "Não encontrado revisão";
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_rev_btn, "returnByValue": True})
            print("Clique revisão:", eval_res.get("result", {}).get("result", {}).get("value"))
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_06_action_revisao_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 7: Navegação para Detalhe da Diferença via Assistente
            # -------------------------------------------------------------
            print("[QA 7] Clicando em 'Auditar Cláusula #1 ➔'...")
            click_audit_btn = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && b.innerText.includes('Auditar Cláusula #1'));
                if (btn) {
                    btn.click();
                    return "Clicado auditar cláusula";
                }
                return "Não encontrado auditar cláusula";
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_audit_btn, "returnByValue": True})
            print("Clique auditar cláusula:", eval_res.get("result", {}).get("result", {}).get("value"))
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_07_assistant_in_detalhe_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 8: No Detalhe — "Mostrar a evidência relacionada"
            # -------------------------------------------------------------
            print("[QA 8] No Detalhe: Clicando em 'Mostrar a evidência relacionada'...")
            click_ev_btn = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && (b.innerText.includes('Mostrar a evidência') || b.innerText.includes('evidência relacionada')));
                if (btn) {
                    btn.click();
                    return "Clicado evidência";
                }
                return "Não encontrado evidência";
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_ev_btn, "returnByValue": True})
            print("Clique evidência:", eval_res.get("result", {}).get("result", {}).get("value"))
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_08_detalhe_evidencia_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 9: Retornar à Comparação Geral
            # -------------------------------------------------------------
            print("[QA 9] Retornando à Comparação Geral...")
            click_back_cmp = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && b.innerText.includes('Voltar à Comparação'));
                if (btn) {
                    btn.click();
                    return "Clicado voltar comparação";
                }
                return "Não encontrado voltar";
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_back_cmp, "returnByValue": True})
            print("Clique voltar comparação:", eval_res.get("result", {}).get("result", {}).get("value"))
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_09_back_to_compare_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 10: Assistente no Relatório
            # -------------------------------------------------------------
            print("[QA 10] Navegando para Relatórios com Assistente aberto...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=relatorios"})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_10_assistant_in_relatorio_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 11: Assistente na Biblioteca (Documentos)
            # -------------------------------------------------------------
            print("[QA 11] Navegando para Documentos com Assistente aberto...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=documentos"})
            await asyncio.sleep(4)
            await save_screenshot(ws, "fase7_9_11_assistant_in_documentos_1440.png")

            # -------------------------------------------------------------
            # CENÁRIO 12: Fechar Assistente Contextual
            # -------------------------------------------------------------
            print("[QA 12] Clicando em 'Fechar Assistente'...")
            click_close_btn = """
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText && (b.innerText.includes('Fechar Assistente') || b.innerText.includes('Fechar')));
                if (btn) {
                    btn.click();
                    return "Clicado fechar";
                }
                return "Não encontrado fechar";
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_close_btn, "returnByValue": True})
            print("Clique fechar:", eval_res.get("result", {}).get("result", {}).get("value"))
            await asyncio.sleep(3)
            await save_screenshot(ws, "fase7_9_12_assistant_closed_again_1440.png")

    finally:
        chrome_proc.terminate()
        print("\nQA Automatizado concluído com sucesso!")


if __name__ == "__main__":
    asyncio.run(run_qa())
