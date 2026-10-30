# openapi-doctor 🩺

[![CI](https://github.com/slopggobblercobbler81/openapi-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/slopggobblercobbler81/openapi-doctor/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![OpenAPI 3.0 & 3.1](https://img.shields.io/badge/OpenAPI-3.0%20%7C%203.1-brightgreen.svg)](https://www.openapis.org/)

A production-grade, zero-compromise OpenAPI 3.0 & 3.1 specification linter and automated autofixer. Designed for high-velocity API development, CI/CD pipelines, and pre-commit automation.

---

## 🌟 Key Features

- **Multi-Version Support**: Seamlessly parses and validates both **OpenAPI 3.0.x** and **OpenAPI 3.1.x** specifications in YAML or JSON format.
- **Accurate Line & Column Mapping**: Pinpoints syntax, schema, and structural issues down to the exact line and column numbers using YAML source AST mappings.
- **Comprehensive Rule Suite**:
  - `missing-response-description`: Detects empty or omitted HTTP response descriptions; autofixes with canonical RFC-standard descriptions (e.g., 200 -> "OK", 201 -> "Created", 404 -> "Not Found").
  - `broken-ref` / `undefined-schema`: Detects dangling `$ref` pointers (e.g. `#/components/schemas/NonExistent`); can automatically generate placeholder object schemas.
  - `unused-component`: Finds unreferenced schemas, responses, parameters, and security definitions bloating specifications; can prune dead declarations.
  - `missing-operation-id`: Ensures every endpoint operation has a uniquely identifiable `operationId`.
  - `duplicate-operation-id`: Prevents code generator collisions by catching duplicate IDs across paths and verbs.
  - `invalid-operation-id`: Enforces consistent naming conventions (camelCase, snake_case, PascalCase, or kebab-case).
  - `undefined-security-scheme`: Verifies that security requirements map directly to declared components in `securitySchemes`.
  - `invalid-security-scope`: Audits OAuth2 / OpenID Connect scopes in operation requirements against scheme declarations.
  - `missing-path-parameter`: Catches path template variables (e.g., `/users/{userId}`) missing required parameter definitions in `parameters`.
  - `unused-path-parameter`: Warns when parameters marked `in: path` do not exist in the path URL template.
- **Automated Fix Engine**:
  - In-place modifications or output redirection (`--output spec.fixed.yaml`).
  - Automatic backup file generation (`--backup` creates `.bak`).
  - Safe dry-run mode (`--dry-run`) to simulate fixes without writing to disk.
  - Selective rule execution (`--rules missing-response-description,undefined-schema`).
- **Flexible Reporting**:
  - Rich ANSI colorized terminal output with context summaries.
  - Machine-readable `--format json` for tooling integration.
  - GitHub Actions Workflow Command formatting (`--format github`) for instant PR annotations.
  - Clean `--format markdown` for CI step summaries and pull request comments.
- **Zero-Dependency Core**: Only depends on `PyYAML`, keeping installation lightweight and fast.

---

## 📦 Installation

Install from source:

```bash
git clone https://github.com/slopggobblercobbler81/openapi-doctor.git
cd openapi-doctor
pip install .
```

For development and running tests:

```bash
pip install -e ".[test]"
```

---

## 🚀 Quickstart & Commands

### 1. `openapi-doctor check` (or `openapi-doctor lint`)

Lints OpenAPI specifications for errors, warnings, and anti-patterns.

```bash
# Lint a single specification file
openapi-doctor check openapi.yaml

# Lint multiple files or recursive directories
openapi-doctor check specs/ src/api/

# Enable strict mode (treat warnings as errors, exit code 1)
openapi-doctor check openapi.yaml --strict

# Output formats: text, json, github, markdown
openapi-doctor check openapi.yaml --format json
openapi-doctor check openapi.yaml --format github
openapi-doctor check openapi.yaml --format markdown

# Disable terminal color codes
openapi-doctor check openapi.yaml --no-color

# Use custom configuration file
openapi-doctor check openapi.yaml -c .openapi-doctor.yaml
```

### 2. `openapi-doctor fix`

Automatically repairs fixable issues such as missing response descriptions or dangling schema references.

```bash
# Preview proposed fixes without altering files
openapi-doctor fix openapi.yaml --dry-run

# Automatically repair in-place and create a .bak backup
openapi-doctor fix openapi.yaml --backup

# Apply fixes and write result to a new file
openapi-doctor fix openapi.yaml -o openapi.fixed.yaml

# Fix only specific rules
openapi-doctor fix openapi.yaml --rules missing-response-description

# Fix in JSON reporting mode for CI scripting
openapi-doctor fix openapi.yaml --dry-run --format json
```

---

## ⚙️ Configuration

`openapi-doctor` automatically discovers configuration files in the working directory tree:
- `.openapi-doctor.yaml` or `.openapi-doctor.yml`
- `.openapi-doctor.json`
- `pyproject.toml` (under `[tool.openapi-doctor]`)

### Example `.openapi-doctor.yaml`

```yaml
# Strict mode: warnings cause exit code 1
strict: false

# Default reporter format: text, json, github, markdown
format: text

# Path patterns to ignore during directory scans
ignore_paths:
  - "**/test/**"
  - "**/vendor/**"
  - "**/*.bak"

# Configure individual rules: error, warning, info, off
rules:
  missing-response-description: error
  broken-ref: error
  undefined-schema: error
  unused-component: warning
  missing-operation-id: warning
  duplicate-operation-id: error
  invalid-operation-id: info
  undefined-security-scheme: error
  invalid-security-scope: warning
  missing-path-parameter: error
  unused-path-parameter: error
```

### Example `pyproject.toml`

```toml
[tool.openapi-doctor]
strict = true
format = "text"
ignore_paths = ["specs/legacy/**"]

[tool.openapi-doctor.rules]
missing-response-description = "error"
unused-component = "warning"
```

---

## 🔄 GitHub Actions CI Integration

Add `openapi-doctor` directly into your GitHub Actions workflow for automated PR checks:

```yaml
name: OpenAPI Linter

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install openapi-doctor
        run: pip install git+https://github.com/slopggobblercobbler81/openapi-doctor.git

      - name: Lint API Specs with GitHub Annotations
        run: openapi-doctor check specs/ --format github --strict
```

---

## 🧪 Testing

Run the full unit test suite with `pytest`:

```bash
pytest
```

Run test suite with coverage report:

```bash
pytest --cov=openapi_doctor --cov-report=term-missing
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 slopggobblercobbler81
