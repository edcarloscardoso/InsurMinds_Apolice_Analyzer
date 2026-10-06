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
        targets = requests.get("http://localhost:9222/json").json()
        page_target = [t for t in targets if t.get("type") == "page"][0]
        ws_url = page_target["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=50 * 1024 * 1024) as ws:
            await cdp_command(ws, "Page.enable")
            await cdp_command(ws, "Runtime.enable")

            # 1. 1440x900
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1440,
                "height": 900,
                "deviceScaleFactor": 1,
                "mobile": False
            })

            print("Navegando para Documentos (Biblioteca)...")
            await cdp_command(ws, "Page.navigate", {"url": "http://localhost:8503/?page=documentos"})
            await asyncio.sleep(4)

            import base64
            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_1440 = os.path.join(ARTIFACT_DIR, "biblioteca_page_1440x900.png")
            with open(shot_1440, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_1440}")

            # 2. 1366x768
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1366,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1)
            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_1366 = os.path.join(ARTIFACT_DIR, "biblioteca_page_1366x768.png")
            with open(shot_1366, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_1366}")

            # 3. 1024x768
            await cdp_command(ws, "Emulation.setDeviceMetricsOverride", {
                "width": 1024,
                "height": 768,
                "deviceScaleFactor": 1,
                "mobile": False
            })
            await asyncio.sleep(1)
            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_1024 = os.path.join(ARTIFACT_DIR, "biblioteca_page_1024x768.png")
            with open(shot_1024, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_1024}")

            # 4. Expand metadata drawer
            print("Abrindo detalhes e metadados de uma apólice...")
            expand_expr = """
            (() => {
                const expanders = Array.from(document.querySelectorAll('[data-testid="stExpander"] details summary'));
                if (expanders.length > 0) {
                    expanders[0].click();
                    return 'EXPANDED_METADATA';
                }
                return 'NO_EXPANDER';
            })()
            """
            eval_exp = await cdp_command(ws, "Runtime.evaluate", {"expression": expand_expr, "returnByValue": True})
            print("Resultado expansão:", eval_exp.get("result", {}).get("value"))
            await asyncio.sleep(2)

            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_meta = os.path.join(ARTIFACT_DIR, "biblioteca_expanded_metadata.png")
            with open(shot_meta, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_meta}")

            # 5. Test button 'Retomar Comparação'
            print("Testando clique em 'Retomar Comparação'...")
            click_resume = """
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const btn = buttons.find(b => b.innerText.includes('Retomar Comparação'));
                if (btn) {
                    btn.click();
                    return 'CLICKED_RESUME';
                }
                return 'NO_RESUME_BTN';
            })()
            """
            eval_res = await cdp_command(ws, "Runtime.evaluate", {"expression": click_resume, "returnByValue": True})
            print("Resultado Retomar:", eval_res.get("result", {}).get("value"))
            await asyncio.sleep(4)

            shot_res = await cdp_command(ws, "Page.captureScreenshot", {"format": "png"})
            shot_resumed = os.path.join(ARTIFACT_DIR, "comparacao_apos_retomada.png")
            with open(shot_resumed, "wb") as f:
                f.write(base64.b64decode(shot_res["result"]["data"]))
            print(f"Screenshot salvo: {shot_resumed}")

    finally:
        chrome_proc.terminate()
        subprocess.run("lsof -ti:9222 | xargs -r kill -9", shell=True)

if __name__ == "__main__":
    asyncio.run(run_qa())
