# API Contracts: Config Workstreams

## GET /config/workstreams

Returns the current state of all evaluation workstreams, resolved from overrides + defaults.

### Response `200 OK`
```json
{
  "ws_a": false,
  "ws_b": false,
  "ws_c": false,
  "ws_d": false,
  "ws_e": false
}
```

---

## PATCH /config/workstreams

Updates workstream flags. Partial update — only provided keys are modified.

### Request Body
```json
{
  "ws_a": true,
  "ws_c": true
}
```

### Response `200 OK`
```json
{
  "ws_a": true,
  "ws_b": false,
  "ws_c": true,
  "ws_d": false,
  "ws_e": false,
  "applies_to": "next_session"
}
```

### Errors
- `422` — Invalid key or non-boolean value
- `500` — Failed to persist overrides file

---

## GET /config/workstreams/health

Returns availability status of external dependencies per workstream.

### Response `200 OK`
```json
{
  "ws_a": {
    "available": true,
    "missing_dependencies": [],
    "degraded_services": []
  },
  "ws_b": {
    "available": true,
    "missing_dependencies": [],
    "degraded_services": []
  },
  "ws_c": {
    "available": true,
    "missing_dependencies": [],
    "degraded_services": []
  },
  "ws_d": {
    "available": false,
    "missing_dependencies": [],
    "degraded_services": ["openalex_timeout"]
  },
  "ws_e": {
    "available": true,
    "missing_dependencies": ["google_factcheck_api_key"],
    "degraded_services": []
  }
}
```

### Errors
- `500` — Health check infrastructure error
