import os
import json
import base64
import asyncio
from typing import List, Optional
# ★追加: Request をインポート
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, UploadFile, File, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === WebSocket管理 ===
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"🔌 Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        print(f"🔌 Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                print(f"Broadcast error: {e}")

manager = ConnectionManager()

# === ルーティング (セキュリティ強化版) ===

@app.get("/")
async def get_index(request: Request, key: Optional[str] = None):
    """
    ルートアクセス制御:
    1. クッキー 'ryoshian_auth' を持っているか確認 -> OKならindex表示
    2. URLパラメータ ?key=SECRET があるか確認 -> OKならクッキーを焼いてindex表示
    3. どちらも無ければ info.html へリダイレクト
    """
    
    # 設定したいパスワード（自由に変更してください）
    SECRET_KEY = "gokuraku2045"
    
    # クッキーチェック
    auth_cookie = request.cookies.get("ryoshian_auth")
    
    # 認証判定
    is_cookie_ok = (auth_cookie == "granted")
    is_key_ok = (key == SECRET_KEY)
    
    if is_cookie_ok or is_key_ok:
        # === 認証OK: index.html を返す ===
        if os.path.exists("static/index.html"):
            response = FileResponse("static/index.html")
        else:
            response = FileResponse("index.html")
        
        # パスワードで入った場合は、次回用にクッキー(通行証)を渡す
        if is_key_ok:
            # 30日間有効なクッキーをセット
            response.set_cookie(key="ryoshian_auth", value="granted", max_age=60*60*24*30)
            
        return response
    
    # === 認証NG: info.html へ飛ばす ===
    return RedirectResponse(url="/static/info.html")

# 静的ファイルマウント
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
else:
    app.mount("/static", StaticFiles(directory="."), name="static")
    # app.mount("/", ... ) はルートと競合するため削除または注意して使用

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# === Q1-Q19対応フォーム受信 ===
@app.post("/submit")
async def handle_form(
    q1: str = Form(""),  # Nickname
    q2: str = Form(""),  # Age
    q3: str = Form(""),  # Color
    q4_1: int = Form(0), # Time
    q4_2: int = Form(0), # Weather
    q4_3: int = Form(0), # Season
    q5: int = Form(0),   # Approach
    q6_1: int = Form(0), # Place
    q6_2: int = Form(0), # Sound
    q6_3: int = Form(0), # Sense
    q7: int = Form(0),   # Scent
    q8: str = Form(""),  # Destination
    q9: int = Form(0),   # Wish
    q10: int = Form(0),  # Drive
    q11: int = Form(0),  # Causality
    q12: int = Form(0),  # Compassion
    q13: int = Form(0),  # Impermanence
    q14: int = Form(0),  # Life/Death
    q15: int = Form(0),  # Heading
    q16: int = Form(0),  # Returning
    q17: str = Form(""), # Legacy (Keep)
    q18: str = Form(""), # Likes
    q19: str = Form(""), # Avoids
    image_b64: str = Form("") # Image
):
    print(f"📩 受信: {q1} ({q2})")
    
    data = {
        "type": "form_submission",
        "identity": { "nickname": q1, "age": q2, "color": q3 },
        "conditions": { "time": q4_1, "weather": q4_2, "season": q4_3 },
        "adolescence": { "approach": q5, "environment_place": q6_1, "environment_sound": q6_2, "environment_sense": q6_3, "scent": q7 },
        "adulthood": { "destination": q8, "wish_direction": q9, "drive": q10 },
        "philosophy": { "causality": q11, "compassion": q12, "impermanence": q13, "life_death": q14 },
        "afterlife": { "heading": q15, "returning": q16 },
        "legacy": { "keep": q17, "likes": q18, "avoids": q19 },
        "has_image": bool(image_b64),
        "image_data": image_b64
    }
    
    await manager.broadcast(data)
    return {"message": "Success"}

# スマホ画像アップロード用
@app.post("/upload-satellite")
async def upload_satellite(session_id: str = Form(...), image: UploadFile = File(...)):
    content = await image.read()
    b64_img = base64.b64encode(content).decode("utf-8")
    message = {
        "type": "satellite_image",
        "session_id": session_id,
        "image_data": b64_img
    }
    await manager.broadcast(message)
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)