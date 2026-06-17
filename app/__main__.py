"""Entrypoint: run the FastAPI app with uvicorn."""
import os

import uvicorn

from .config import settings


def main() -> None:
    port = int(os.environ.get("PORT", settings.web_port))
    uvicorn.run(
        "app.main:app",
        host=settings.web_host,
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
