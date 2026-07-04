# Agent Design — ReAct Engine

## Overview

The agent uses a **ReAct (Reasoning + Acting)** loop with Gemini Pro function calling to handle complex multi-condition scenario queries that simple RAG cannot answer reliably.

---

## When the Agent is Used

| Query Type | Example | Route |
|---|---|---|
| Simple lookup | "What is Law 36.1?" | RAG only |
| Definition | "What is umpire's call?" | RAG only |
| **Scenario** | "Ball pitched outside leg, hit in front, no bat..." | **Agent** |
| **Conditional** | "Can you review height on DRS?" | **Agent** |
| **Comparison** | "What's the difference between ODI and Test DRS?" | **Agent** |

---

## ReAct Loop Flow

```
User Query
    │
    ▼
┌─────────────────────────────────────────────┐
│ Initialize: System prompt + tools + query   │
└─────────────────────────────────────────────┘
    │
    ▼
┌──────────────────┐     ┌──────────────────┐
│  Gemini Pro      │────→│  Tool Result     │
│  decides next    │←────│  appended to     │
│  action          │     │  conversation    │
└──────────────────┘     └──────────────────┘
    │                           │
    │ (tool call)              │
    └──────────────────────────┘
    │
    │ (no tool call — final answer)
    ▼
┌─────────────────────────────────────────────┐
│ Guardrail checks → Response                 │
└─────────────────────────────────────────────┘
```

### Loop Termination Conditions
1. Agent emits a final answer (no tool call requested)
2. Max turns reached (default: 10)
3. Guardrail failure triggers regeneration

---

## Tool Definitions

### 1. retrieve_law(law_number, format)

Retrieves the exact text of a specific law from the vector database.

**Parameters:**
- `law_number` (string, required): e.g., "36.1", "25.3"
- `format` (string, optional): "test", "odi", "t20i", "all"

**Returns:**
```json
{
  "law_number": "36.1",
  "title": "LBW — Pitching",
  "text": "...the ball pitches in line with the stumps or on the off side...",
  "formats": ["test", "odi", "t20i"],
  "authority": "icc",
  "year": 2025
}
```

### 2. check_condition(condition, law_number, scenario)

Checks whether a specific condition is satisfied in the given scenario. Uses the condition graphs from `scenarios.py`.

**Parameters:**
- `condition` (string, required): The condition to evaluate
- `law_number` (string, required): The law this condition falls under
- `scenario` (string, required): Full user scenario description

**Returns:**
```json
{
  "condition_met": false,
  "reasoning": "Ball pitched outside leg stump. Per Law 36.1, this is automatic NOT OUT regardless of other conditions.",
  "law_reference": "Law 36.1 — Pitching",
  "terminal": true
}
```

The `terminal: true` flag tells the agent this condition ends the analysis — no need to check further.

### 3. compare_formats(law_number)

Compares how a specific law differs across Test, ODI, and T20I formats.

**Parameters:**
- `law_number` (string, required)

**Returns:**
```json
{
  "law_number": "25.3",
  "differences": [
    {"test": "2 DRS reviews per innings"},
    {"odi": "2 DRS reviews per innings"},
    {"t20i": "2 DRS reviews per innings"}
  ],
  "note": "No difference in DRS reviews across formats from 2026 onwards (all formats use 2 reviews per innings)"
}
```

### 4. get_amendments(law_number)

Returns recent changes to a law.

**Parameters:**
- `law_number` (string, required)

**Returns:**
```json
{
  "law_number": "25.3",
  "amendments": [
    {
      "year": 2025,
      "change": "Increased from 2 to 4 DRS reviews per innings",
      "effective": "June 2025"
    },
    {
      "year": 2024,
      "change": "Umpire's call retained on ball-tracking",
      "effective": "March 2024"
    }
  ]
}
```

### 5. get_scenario_steps(scenario_type, format)

Returns the ordered checklist of conditions the agent must verify for a given scenario type.

**Parameters:**
- `scenario_type` (string, required): "lbw", "run_out", "stumping", "hit_wicket", "obstructing", "no_ball", "wide", "drs_review"
- `format` (string, optional): "test", "odi", "t20i", "all"

**Returns:**
```json
{
  "scenario_type": "lbw",
  "format": "all",
  "conditions": [
    { "id": 1, "description": "Ball pitches in line or on off side", "law": "36.1", "terminal": true },
    { "id": 2, "description": "Impact in line with stumps", "law": "36.2", "terminal": false },
    { "id": 3, "description": "Ball would hit stumps", "law": "36.3", "terminal": true },
    { "id": 4, "description": "Bat not involved before pad", "law": "36.4", "terminal": false },
    { "id": 5, "description": "No-shot exception handled", "law": "36.5", "terminal": true }
  ]
}
```

---

## Condition Graphs (Scenarios)

Each scenario type has a pre-defined condition graph stored in `scenarios.py`. These graphs define:

1. The ordered list of conditions to check
2. Which conditions are **terminal** (if false, stop — no need to check further)
3. The law number associated with each condition
4. Human-readable explanations for pass/fail

See `app/agent/scenarios.py` (my code) for full condition graphs for all 10+ scenario types.

---

## Agent Safety

- Max 10 tool calls per query (prevents infinite loops)
- Timeout: 60 seconds total for agent execution
- If guardrails fail the final answer → return safe refusal message
- If agent produces no answer after 10 turns → return timeout message
