"""In OpenAPI schema của FastAPI app ra stdout — dùng cho pipeline sinh TS client.

Chạy: uv run python scripts/export_openapi.py > ../web/openapi.json
"""

import json
import sys

from api.main import app


def main() -> None:
    json.dump(app.openapi(), sys.stdout, indent=2)


if __name__ == "__main__":
    main()
