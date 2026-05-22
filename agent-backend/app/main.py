"""FastAPI 主入口"""

import logging
import sys
import time
from pathlib import Path

# 确保项目根目录在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes import router

# 配置日志：输出到文件和控制台
_log_file = Path(__file__).resolve().parent.parent / "output" / "pipeline.log"
_log_file.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(str(_log_file), encoding="utf-8"),
        logging.StreamHandler(),
    ],
    force=True,
)

app = FastAPI(
    title="Video Agent API",
    description="AI document-to-video generation with HyperFrames",
    version="0.1.0",
)

# 请求日志中间件
@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    elapsed = round(time.time() - start, 3)
    logging.getLogger("uvicorn.access").info(
        f"[Backend] {request.method} {request.url.path} -> {response.status_code} ({elapsed}s)"
    )
    return response

# CORS — 允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


def main():
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        timeout_keep_alive=1800,  # SSE 长连接可能需要 30 分钟以上
    )


if __name__ == "__main__":
    main()
