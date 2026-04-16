"""Export OpenAPI specification for frontend contract.

Usage:
    python scripts/export_openapi.py

Outputs:
    - openapi.json: Full OpenAPI 3.1 spec
    - openapi.yaml: YAML format (human-readable)

Frontend should use this as the single source of truth for API contracts.
"""

import json
import yaml
from pathlib import Path

from app.main import app


def export_openapi():
    """Export OpenAPI spec to JSON and YAML files."""
    output_dir = Path(__file__).parent.parent / "docs" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)

    openapi_schema = app.openapi()

    json_path = output_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    print(f"✅ Exported OpenAPI JSON: {json_path}")

    yaml_path = output_dir / "openapi.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, default_flow_style=False, allow_unicode=True)
    print(f"✅ Exported OpenAPI YAML: {yaml_path}")

    print(f"\n📊 API Summary:")
    print(f"   - Title: {openapi_schema['info']['title']}")
    print(f"   - Version: {openapi_schema['info']['version']}")
    print(f"   - Paths: {len(openapi_schema['paths'])}")

    print(f"\n🔗 Available endpoints:")
    for path, methods in openapi_schema["paths"].items():
        for method in methods:
            if method in ["get", "post", "put", "patch", "delete"]:
                summary = methods[method].get("summary", "")
                print(f"   {method.upper():6} {path:40} {summary}")

    return openapi_schema


if __name__ == "__main__":
    export_openapi()
