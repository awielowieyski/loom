"""Entry point: uv run python -m loom.api"""

import uvicorn

from loom.settings import LoomSettings


def main() -> None:
    settings = LoomSettings()
    uvicorn.run(
        "loom.api.app:create_app",
        factory=True,
        host=settings.api.host,
        port=settings.api.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
