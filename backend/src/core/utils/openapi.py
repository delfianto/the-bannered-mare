import json
import os
from pathlib import Path

from src.main import app


def get_project_root() -> Path:
    """Find the project root by searching for a marker file."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    # Fallback to current behavior if marker not found
    return current.parents[3]


def generate_openapi_schema(output_path: str | None = None):
    """
    Generates the OpenAPI schema for the FastAPI application and saves it to a JSON file.
    Defaults to openapi.json in the project root.
    """
    project_root = get_project_root()

    if output_path is None:
        output_path = str(project_root / "openapi.json")

    openapi_schema = app.openapi()

    # Ensure directory exists if a custom path is provided
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"Successfully generated OpenAPI schema at: {output_path}")


if __name__ == "__main__":
    generate_openapi_schema()
