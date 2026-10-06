import asyncio
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

async def run_qa():
    # Start Chrome Headless on 9222
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
        # Get page websocket URL
        targets = requests.get("http://localhost:9222/json").json()
        page_target = [t for t in targets if t.get("type") == "page"][0]
        ws_url = page_target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            # Enable Page and Runtime
            await cdp_command(ws, "Page.enable")
            await cdp_command(ws, "Runtime.enable")

            # Set viewport 1440x900
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1440,
                "height": 900,
                "deviceScaleFactor": 1,
                "mobile": False
            })

            # Navigate to comparacoes
            print("Navegando para comparacoes...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=comparacoes"})
            await asyncio.sleep(4)

            # Click Auditar Detalhe button
            print("Clicando em 'Auditar Detalhe'...")
            click_expr = """
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b => b.innerText.includes('Auditar Detalhe'));
                if (btn) {
                    btn.click();
                    return 'CLICKED_DETAIL';
                }
                return 'NOT_FOUND: ' + buttons.map(b => b.innerText).join(' | ');
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_expr, "returnByValue": True})
            print("Resultado do clique:", eval_res.get("result", {}).get("value"))
            await asyncio.sleep(4)

            # Capture screenshot of Detalhe 1440x900
            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            import base64
            img_data = base64.b64decode(shot_res["result"]["data"])
            shot_1440 = os.path.join(ARTIFACT_DIR, "detalhe_diferenca_1440x900.png")
            with open(shot_1440, "wb") as f:
                f.write(img_data)
            print(f"Screenshot salvo: {shot_1440}")

            # Capture 1366x768
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1)
            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_1366 = os.path.join(ARTIFACT_DIR, "detalhe_diferenca_1366x768.png")
            with open(shot_1366, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_1366}")

            # Capture 1024x768
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1024,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1)
            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_1024 = os.path.join(ARTIFACT_DIR, "detalhe_diferenca_1024x768.png")
            with open(shot_1024, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_1024}")

            # Test Navigation: Click Proximo
            print("Testando navegação Próximo ➔...")
            next_expr = """
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b => b.innerText.includes('Próximo'));
                if (btn) {
                    btn.click();
                    return 'CLICKED_NEXT';
                }
                return 'NEXT_NOT_FOUND';
            })()
            """
            eval_next = await cdp_command(ws, "Runtime.evaluate", {"expression": next_expr, "returnByValue": True})
            print("Resultado Próximo:", eval_next.get("result", {}).get("value"))
            await asyncio.sleep(3)

            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_next = os.path.join(ARTIFACT_DIR, "detalhe_diferenca_next_item.png")
            with open(shot_next, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_next}")

            # Test Navigation: Voltar a Comparacao
            print("Testando Voltar à Comparação...")
            back_expr = """
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b => b.innerText.includes('Voltar à Comparação'));
                if (btn) {
                    btn.click();
                    return 'CLICKED_BACK';
                }
                return 'BACK_NOT_FOUND';
            })()
            """
            eval_back = await cdp_command(ws, "Runtime.evaluate", {"expression": back_expr, "returnByValue": True})
            print("Resultado Voltar:", eval_back.get("result", {}).get("value"))
            await asyncio.sleep(3)

            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_back = os.path.join(ARTIFACT_DIR, "comparacao_apos_voltar.png")
            with open(shot_back, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_back}")

    finally:
        chrome_proc.terminate()
        subprocess.run("lsof -ti:9222 | xargs -r kill -9", shell=True)

if __name__ == "__main__":
    asyncio.run(run_qa())
