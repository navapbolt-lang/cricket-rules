# API Reference

## Base URL

```
Production: https://api.cricketrules.ai/api/v1
Local:      http://localhost:8000/api/v1
```

## Authentication

All requests require an `X-API-Key` header.

```http
X-API-Key: <partner_api_key>
```

---

## Endpoints

### POST /chat

Send a query and receive a complete answer.

**Request:**
```json
{
  "query": "Can DRS overturn umpire's call on height?",
  "format": "odi",
  "context": "match",
  "session_id": "abc-123"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| query | string | yes | The cricket rules question |
| format | string | no | "test", "odi", "t20i", or null for auto-detect |
| context | string | no | "match", "article", "general" (affects suggestions) |
| session_id | string | no | For conversation continuity |

**Response:**
```json
{
  "answer": "No, umpire's call on height cannot be overturned by DRS. When the on-field umpire gives 'not out' and ball-tracking shows the ball missing the stumps or clipping the bails (umpire's call), the original decision stands regardless of the review...",
  "citations": [
    {
      "law_number": "36.3",
      "text": "If the ball would have hit the stumps but the umpire is uncertain, the original decision stands.",
      "formats": ["odi", "t20i"],
      "authority": "icc",
      "year": 2025
    }
  ],
  "confidence": 0.94,
  "suggested_questions": [
    "What is umpire's call?",
    "How many DRS reviews per innings in ODI?"
  ],
  "format_used": "odi",
  "guardrail_status": "passed"
}
```

---

### POST /chat/stream

Same as `/chat` but returns response as Server-Sent Events.

**Events:**
```
data: {"type": "status", "message": "Retrieving relevant laws..."}
data: {"type": "status", "message": "Analyzing your scenario..."}
data: {"type": "token", "text": "Based on Law 36.1"}
data: {"type": "token", "text": ", the ball must pitch in line with the stumps."}
data: {"type": "citation", "citation": {...}}
data: {"type": "done", "response": { ...full ChatResponse... }}
```

---

### GET /suggestions

Returns suggested questions based on context.

**Query Parameters:**
- `format` (optional): "test", "odi", "t20i"
- `context` (optional): "match", "article", "general"

**Response:**
```json
{
  "suggestions": [
    {"question": "What is the LBW law?", "category": "popular"},
    {"question": "How does DRS work in ODI?", "category": "format_specific"}
  ]
}
```

---

### POST /feedback

Submit feedback on a response.

**Request:**
```json
{
  "session_id": "abc-123",
  "query": "What is Law 36.1?",
  "response": "...",
  "vote": "down",
  "reason": "wrong citation",
  "correct_answer": "Law 36.1 is about..."
}
```

---

## Error Codes

| Status | Code | Meaning |
|---|---|---|
| 401 | UNAUTHORIZED | Missing or invalid API key |
| 429 | RATE_LIMITED | Partner quota exceeded |
| 422 | VALIDATION_ERROR | Invalid request body |
| 500 | INTERNAL_ERROR | Something went wrong |
| 503 | GUARDRAIL_REJECTED | Response failed safety checks |
