import json
import urllib.request
import sys
from pathlib import Path

def generate_markdown():
    try:
        req = urllib.request.Request("http://127.0.0.1:8001/openapi.json")
        with urllib.request.urlopen(req) as response:
            openapi = json.loads(response.read())
    except Exception as e:
        print(f"Failed to fetch openapi.json: {e}")
        sys.exit(1)

    md = []
    md.append("# API Reference\n")
    md.append("This document provides a comprehensive reference for the E-Library Management System API.\n")
    
    # 1. Quick Reference Table
    md.append("## API Quick Reference\n")
    md.append("| Method | Endpoint | Authentication | Role | Purpose |")
    md.append("|---|---|---|---|---|")
    
    paths = openapi.get("paths", {})
    
    # Process paths for the table
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.lower() not in ['get', 'post', 'put', 'patch', 'delete']:
                continue
            
            summary = operation.get("summary", "")
            security = operation.get("security", [])
            auth = "Bearer Token" if security else "None"
            role = "Any"
            if auth != "None":
                desc = operation.get("description", "").lower()
                if "admin" in desc or "administrator" in desc or "admin role" in summary.lower():
                    role = "ADMIN"
                else:
                    role = "USER"
            
            md.append(f"| {method.upper()} | `{path}` | {auth} | {role} | {summary} |")
            
    md.append("\n## Authentication Guide\n")
    md.append("The API uses OAuth2 with Bearer Tokens (JWT).")
    md.append("- **Registration**: `POST /api/v1/auth/register`")
    md.append("- **Login**: `POST /api/v1/auth/login/access-token` (requires `username` and `password` form data)")
    md.append("- **Usage**: Provide the token in the `Authorization` header: `Bearer <token>`")
    md.append("- **Local Admin Bootstrap**: Run `python scripts/create_admin.py` locally to create an admin account. No public endpoint exists for self-promotion.\n")

    md.append("## Digital Book & PDF Guide\n")
    md.append("Books that have digital copies uploaded (PDFs) will return `has_digital_copy: true` in their responses.")
    md.append("- **Access**: You must have an `ACTIVE` borrowing to download the PDF.")
    md.append("- **Download**: `GET /api/v1/books/{book_id}/file` returns the binary PDF.")
    md.append("- **Revocation**: Returning the book immediately revokes access to the PDF.\n")

    md.append("## Reading Progress Guide\n")
    md.append("- **Tracking**: Clients can `PUT /api/v1/books/{book_id}/progress` to save progress (requires an active borrowing).")
    md.append("- **History**: `GET /api/v1/reading-progress/me` returns your historical progress across all books, even after return.")
    md.append("- **Stale Detection**: If a book's PDF is updated (content_version increments), progress is preserved but marked `is_stale: true`.\n")

    md.append("## Endpoints Detail\n")
    
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.lower() not in ['get', 'post', 'put', 'patch', 'delete']:
                continue
                
            summary = operation.get("summary", "No Summary")
            md.append(f"### {summary}")
            md.append(f"**`{method.upper()} {path}`**\n")
            
            desc = operation.get("description", "No description provided.")
            md.append(f"{desc}\n")
            
            security = operation.get("security", [])
            auth = "Bearer Token" if security else "None"
            md.append(f"- **Authentication**: {auth}")
            
            if auth != "None":
                role = "ADMIN" if ("admin" in desc.lower() or "administrator" in desc.lower()) else "USER"
                md.append(f"- **Role**: {role}")
            md.append("")
            
            params = operation.get("parameters", [])
            if params:
                md.append("**Parameters:**")
                md.append("| Name | In | Required | Type | Description |")
                md.append("|---|---|---|---|---|")
                for p in params:
                    name = p.get("name")
                    in_ = p.get("in")
                    req = "Yes" if p.get("required") else "No"
                    schema = p.get("schema", {})
                    ptype = schema.get("type", "string")
                    pdesc = p.get("description", "")
                    md.append(f"| `{name}` | {in_} | {req} | {ptype} | {pdesc} |")
                md.append("")
            
            responses = operation.get("responses", {})
            if responses:
                md.append("**Responses:**")
                for code, resp in responses.items():
                    rdesc = resp.get("description", "")
                    md.append(f"- **{code}**: {rdesc}")
            md.append("\n---\n")
            
    out_path = Path(__file__).resolve().parent.parent / "docs" / "API_REFERENCE.md"
    out_path.parent.mkdir(exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))
        
    print(f"API Reference written to {out_path}")

if __name__ == "__main__":
    generate_markdown()
