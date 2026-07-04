"""Widget asset serving routes.
Infrastructure — serves embed.js, styles.css for the embeddable chat widget.
"""

from pathlib import Path
from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

WIDGET_DIR = Path(__file__).resolve().parents[2] / "frontend" / "widget"

router = APIRouter()

CACHE_BUST = "20260627"


@router.get("/widget/embed.js")
async def serve_embed_js():
    path = WIDGET_DIR / "embed.js"
    if not path.exists():
        return Response("/* widget not found */", media_type="application/javascript")
    return FileResponse(path, media_type="application/javascript")


@router.get("/widget/styles.css")
async def serve_widget_css():
    path = WIDGET_DIR / "styles.css"
    if not path.exists():
        return Response("/* widget styles not found */", media_type="text/css")
    return FileResponse(path, media_type="text/css")


@router.get("/")
async def serve_landing():
    path = WIDGET_DIR / "index.html"
    if not path.exists():
        return Response("<!-- landing not found -->", media_type="text/html")
    resp = FileResponse(path, media_type="text/html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@router.get("/demo")
async def serve_demo():
    path = WIDGET_DIR / "template.html"
    if not path.exists():
        return Response("<!-- demo not found -->", media_type="text/html")
    resp = FileResponse(path, media_type="text/html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@router.get("/demo/live")
async def serve_live_demo():
    path = WIDGET_DIR / "demo.html"
    if not path.exists():
        return Response("<!-- live demo not found -->", media_type="text/html")
    resp = FileResponse(path, media_type="text/html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp


@router.get("/simulator")
async def serve_simulator():
    path = WIDGET_DIR / "simulator.html"
    if not path.exists():
        return Response("<!-- simulator not found -->", media_type="text/html")
    resp = FileResponse(path, media_type="text/html")
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    resp.headers["Pragma"] = "no-cache"
    resp.headers["Expires"] = "0"
    return resp
