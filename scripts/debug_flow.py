"""
DEBUG SCRIPT — Step-by-step code flow visualizer.
Run: python scripts/debug_flow.py

This script simulates a full query without needing the API/DB running.
It prints every step so you can understand the flow.
"""

import sys
import os
import re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("=" * 70)
print("DEBUG: Cricket Rules AI - Code Flow")
print("=" * 70)

query = "Ball pitched outside leg, hit in front, no bat, going on to hit off stump"
print("\n[STEP 0] User Query")
print('   Input: "' + query + '"')

print("\n[STEP 1] ChatService.classify_query()")
print("   File: app/services/chat_service.py:169")
print("   Logic: Checks query against scenario patterns:")

q = query.lower()
scenario_patterns = [
    r"what (if|happens)",
    r"(ball|delivery) (pitched|bowled|landed)",
    r"(hit|struck|impact) (in front|outside|on)",
    r"going on to",
    r"no bat",
    r"would have (hit|gone)",
    r"what('s| is) the (decision|call|ruling)",
    r"is (that|this) (out|not out|a (no.?ball|wide))",
]
for pattern in scenario_patterns:
    match = re.search(pattern, q)
    if match:
        print("   [MATCHED] \"" + pattern + "\" -> SCENARIO route")
        break

print("\n[STEP 2] format_router.detect_format()")
print("   File: app/agent/format_router.py:46")
print("   Checks query for: test, odi, t20i keywords")
from app.agent.format_router import detect_format
fmt = detect_format(query)
print("   Detected format: " + fmt.value.upper())

print("\n[STEP 3] Agent.run() - ReAct Loop")
print("   File: app/agent/agent.py:37")
print("   1. Initialize Gemini Pro with system prompt + 5 tools")
print("   2. Send user query to LLM")
print("   3. Gemini decides: call a tool or emit answer directly")
print("")
print("   Tool Options available to Gemini:")
print("    a) retrieve_law(law_number) -> Get exact law text from Qdrant")
print("    b) check_condition(condition, law, scenario) -> Pass/fail")
print("    c) compare_formats(law_number) -> Cross-format differences")
print("    d) get_amendments(law_number) -> Rule changes over time")
print("    e) get_scenario_steps(scenario_type) -> Condition checklist")
print("")

print("[STEP 4] scenarios.get_scenario_graph('lbw')")
print("   File: app/agent/scenarios.py:187")
print("   Returns ordered condition checklist for LBW:")

from app.agent.scenarios import get_scenario_graph
conditions = get_scenario_graph("lbw")
for c in conditions:
    term = "[TERMINAL]" if c.terminal else "[can continue]"
    print("   [" + str(c.id) + "] Law " + c.law + ": " + c.description[:60] + "... " + term)

print("\n[STEP 5] Agent calls check_condition()")
print("   File: app/agent/tools.py:115")
print("   For condition 1: 'Ball pitches in line with stumps or on off side'")
print("   Evaluating against query: '" + query + "'")

scenario_lower = query.lower()
if "outside leg" in scenario_lower:
    print("   [FAIL] - 'outside leg' found in query")
    print("      Ball pitched OUTSIDE LEG - NOT OUT (Law 36.1)")
    print("      This is a TERMINAL condition - agent stops here")
else:
    print("   [PASS] - ball pitched in line")

print("\n[STEP 6] Guardrails Layer")
print("   File: app/services/chat_service.py:182")
print("   Sequential checks before serving response:")

guardrail_steps = [
    ("1. Citation Grounding", "app/guardrails/citation.py",
     "Extracts law numbers from answer, checks they exist in chunks"),
    ("2. Hallucination Detection", "app/guardrails/hallucination.py",
     "Splits answer into claims, verifies each against context"),
    ("3. Format Consistency", "app/guardrails/format_check.py",
     "Ensures answer uses correct format rules"),
]
for name, file, desc in guardrail_steps:
    print("   " + name)
    print("      File: " + file)
    print("      " + desc)

print("\n[STEP 7] ChatResponse returned")
print("   File: app/models/schemas.py:19")
print("   Fields: answer, citations[], confidence, suggested_questions[],")
print("           format_used, guardrail_status")

print("\n" + "=" * 70)
print("FULL PIPELINE FLOW DIAGRAM")
print("=" * 70)
print("""
USER QUERY
    |
    v
+--------------------------+
| classify_query()         |
| -> SCENARIO or SIMPLE    |
+------------+-------------+
             |
     +-------+---------+
     |                 |
     v                 v
+----------+    +-------------+
| SIMPLE   |    | SCENARIO    |
| PATH     |    | PATH        |
|          |    |             |
| retrieve |    | Agent.run() |
| .search  |    |  get_steps  |
| -> 20    |    |  check_cond |
|          |    |  retrieve   |
| rerank   |    |  (loop)     |
| -> top 5 |    +------+------+
|          |           |
| LLM gen  |           |
+-----+----+           |
      |                |
      +-------+--------+
              |
              v
+--------------------------+
| Guardrails               |
| 1. Citation check        |
| 2. Hallucination check   |
| 3. Format check          |
| 4. Confidence gate       |
+------------+-------------+
             |
             v
+--------------------------+
| ChatResponse(answer,     |
|   citations, confidence) |
+--------------------------+
""")

print("=" * 70)
print("HOW TO DEBUG EACH COMPONENT")
print("=" * 70)
print("""
1. Test ingestion alone:
   python -c "from app.ingestion.parser import extract_text; pages = extract_text('data/pdfs/test.pdf')"

2. Test vector search alone:
   python -c "from app.rag.vector_store import VectorStore; v = VectorStore(); print(v.count())"

3. Test retriever alone:
   python -c "from app.rag.retriever import HybridRetriever;
              r = HybridRetriever(vs, embed); chunks = r.search('Law 36.1', {'law_number': '36.1'})"

4. Test a scenario graph:
   python -c "from app.agent.scenarios import get_scenario_graph;
              conds = get_scenario_graph('lbw');
              [print(c.description) for c in conds]"

5. Run API in debug mode:
   uvicorn app.main:app --reload --log-level debug

6. Set breakpoints and step through:
   python -m pdb scripts/debug_flow.py

7. Add print() debugging to any file:
   print(f\"[DEBUG chat_service] query_type={query_type}\")
""")
