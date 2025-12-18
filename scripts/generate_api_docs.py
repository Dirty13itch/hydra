#!/usr/bin/env python3
"""
Generate Markdown API documentation from OpenAPI spec.

Usage:
    python generate_api_docs.py > ../docs/API.md
"""

import json
import sys
import httpx
from collections import defaultdict

API_URL = "http://192.168.1.244:8700/openapi.json"

def fetch_openapi_spec():
    """Fetch the OpenAPI spec from the API."""
    response = httpx.get(API_URL, timeout=30.0)
    return response.json()

def generate_markdown(spec: dict) -> str:
    """Generate markdown documentation from OpenAPI spec."""
    lines = []

    # Title and description
    info = spec.get("info", {})
    lines.append(f"# {info.get('title', 'API Documentation')}")
    lines.append("")
    lines.append(f"**Version:** {info.get('version', 'unknown')}")
    lines.append("")

    if info.get("description"):
        lines.append(info["description"])
        lines.append("")

    # Table of contents - group by tag
    paths = spec.get("paths", {})
    endpoints_by_tag = defaultdict(list)

    for path, methods in paths.items():
        for method, details in methods.items():
            if method in ("get", "post", "put", "delete", "patch"):
                tags = details.get("tags", ["Other"])
                for tag in tags:
                    endpoints_by_tag[tag].append({
                        "method": method.upper(),
                        "path": path,
                        "summary": details.get("summary", ""),
                        "description": details.get("description", ""),
                        "operation_id": details.get("operationId", ""),
                        "parameters": details.get("parameters", []),
                        "request_body": details.get("requestBody"),
                        "responses": details.get("responses", {}),
                    })

    # Table of Contents
    lines.append("## Table of Contents")
    lines.append("")
    for tag in sorted(endpoints_by_tag.keys()):
        anchor = tag.lower().replace(" ", "-").replace("/", "")
        lines.append(f"- [{tag}](#{anchor})")
    lines.append("")

    # Generate documentation for each tag
    for tag in sorted(endpoints_by_tag.keys()):
        lines.append(f"## {tag}")
        lines.append("")

        for endpoint in endpoints_by_tag[tag]:
            # Endpoint header
            lines.append(f"### {endpoint['method']} `{endpoint['path']}`")
            lines.append("")

            if endpoint["summary"]:
                lines.append(f"**{endpoint['summary']}**")
                lines.append("")

            if endpoint["description"]:
                lines.append(endpoint["description"])
                lines.append("")

            # Parameters
            if endpoint["parameters"]:
                lines.append("**Parameters:**")
                lines.append("")
                lines.append("| Name | In | Type | Required | Description |")
                lines.append("|------|----|----|----------|-------------|")
                for param in endpoint["parameters"]:
                    name = param.get("name", "")
                    location = param.get("in", "")
                    schema = param.get("schema", {})
                    param_type = schema.get("type", "any")
                    required = "Yes" if param.get("required") else "No"
                    desc = param.get("description", "")
                    lines.append(f"| `{name}` | {location} | {param_type} | {required} | {desc} |")
                lines.append("")

            # Request body
            if endpoint["request_body"]:
                lines.append("**Request Body:**")
                lines.append("")
                content = endpoint["request_body"].get("content", {})
                for content_type, schema_info in content.items():
                    lines.append(f"Content-Type: `{content_type}`")
                    if schema_info.get("schema", {}).get("$ref"):
                        ref = schema_info["schema"]["$ref"].split("/")[-1]
                        lines.append(f"Schema: `{ref}`")
                lines.append("")

            # Responses
            if endpoint["responses"]:
                lines.append("**Responses:**")
                lines.append("")
                for status, response in endpoint["responses"].items():
                    desc = response.get("description", "")
                    lines.append(f"- `{status}`: {desc}")
                lines.append("")

            lines.append("---")
            lines.append("")

    # Summary statistics
    lines.append("## API Statistics")
    lines.append("")
    total_endpoints = sum(len(v) for v in endpoints_by_tag.values())
    lines.append(f"- **Total Endpoints:** {total_endpoints}")
    lines.append(f"- **Tag Categories:** {len(endpoints_by_tag)}")
    lines.append("")
    lines.append("### Endpoints by Category")
    lines.append("")
    lines.append("| Category | Endpoints |")
    lines.append("|----------|-----------|")
    for tag in sorted(endpoints_by_tag.keys()):
        lines.append(f"| {tag} | {len(endpoints_by_tag[tag])} |")
    lines.append("")

    return "\n".join(lines)

def main():
    try:
        spec = fetch_openapi_spec()
        markdown = generate_markdown(spec)
        print(markdown)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
