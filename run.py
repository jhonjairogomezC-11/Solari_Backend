"""Arranque del servidor en Windows con el event loop correcto para psycopg.

psycopg 3 async NO funciona con el ProactorEventLoop (default en Windows). uvicorn
no respeta de forma fiable la policy global, así que creamos nosotros el
SelectorEventLoop y ejecutamos el servidor dentro de él.

Uso:  uv run python run.py
"""

from __future__ import annotations

import asyncio
import os
import sys

import uvicorn


def main() -> None:
    host = os.getenv("SOLARI_HOST", "127.0.0.1")
    # Puerto 9000 por defecto (8001 y 8080 caen en el rango excluido por Windows/Hyper-V
    # en algunas máquinas, provocando winerror 10013). Configurable con SOLARI_PORT.
    port = int(os.getenv("SOLARI_PORT", "9000"))
    config = uvicorn.Config(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        loop="asyncio",
    )
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        # Loop Selector explícito para compatibilidad con psycopg async.
        loop = asyncio.SelectorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(server.serve())
        finally:
            loop.close()
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
