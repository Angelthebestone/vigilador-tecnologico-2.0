# API Contracts: Config Prompts

## GET /config/prompts

Lists all evaluation prompt templates with metadata.

### Response `200 OK`
```json
{
  "templates": [
    {"name": "assumption_detection", "modified": false, "size": 1024},
    {"name": "counterfactual", "modified": false, "size": 896},
    {"name": "falsification", "modified": true, "size": 2048},
    {"name": "query_expand", "modified": false, "size": 512},
    {"name": "stakeholder_academic", "modified": false, "size": 768},
    {"name": "stakeholder_competitor", "modified": false, "size": 768},
    {"name": "stakeholder_investor", "modified": false, "size": 768},
    {"name": "stakeholder_regulator", "modified": false, "size": 768}
  ]
}
```

---

## GET /config/prompts/{name}

Returns the full content of a prompt template. Returns the override if it exists, otherwise the default.

### Path Parameters
| Param | Type | Description |
|-------|------|-------------|
| `name` | `str` | Template name (e.g., `assumption_detection`) |

### Response `200 OK`
```json
{
  "name": "assumption_detection",
  "content": "You are an expert...\nIdentify implicit assumptions...",
  "modified": false,
  "default_content": "You are an expert...\nIdentify implicit assumptions...",
  "size": 1024
}
```

### Errors
- `404` — Template not found

---

## PUT /config/prompts/{name}

Updates a prompt template's override content.

### Path Parameters
| Param | Type | Description |
|-------|------|-------------|
| `name` | `str` | Template name |

### Request Body
```json
{
  "content": "You are an expert in...\nDetect implicit assumptions by..."
}
```

### Response `200 OK`
```json
{
  "name": "assumption_detection",
  "modified": true,
  "size": 1200
}
```

### Errors
- `404` — Template not found
- `422` — Content exceeds max size (100KB)
- `500` — Failed to persist override

---

## POST /config/prompts/{name}/restore

Restores a prompt template to its default content (deletes the override file).

### Path Parameters
| Param | Type | Description |
|-------|------|-------------|
| `name` | `str` | Template name |

### Response `200 OK`
```json
{
  "name": "assumption_detection",
  "modified": false,
  "restored": true
}
```

### Errors
- `404` — Template not found
- `500` — Failed to delete override
