# LangChain × AI Shift Scheduler — Feature Brainstorm

How we can use [LangChain](https://docs.langchain.com) (agents, RAG, structured output, memory) to add value to the shift scheduling app without replacing the existing OR-Tools solver.

---

## LangChain capabilities we can use

| Capability | What it does | Scheduler use case |
|------------|--------------|--------------------|
| **Agents (ReAct)** | LLM + tools: reason, call tools, return answer | Natural-language commands → update overrides, query schedule, explain results |
| **RAG** | Retrieve from docs → generate answer | Answer questions from policy (context.md, roster format), or from the current schedule |
| **Structured output** | LLM returns JSON/Pydantic | Parse free text → `manual_overrides` / `off_requests` / config suggestions |
| **Memory** | Conversation history | Multi-turn “schedule assistant” that remembers context |
| **Chains** | Sequential LLM steps | Validate → extract → confirm before applying changes |

---

## Feature ideas (by theme)

### 1. Natural-language schedule assistant (Agent + tools)

**Idea:** A chat panel (sidebar or tab) where the manager types in plain English; an agent translates that into actions using tools.

**Example utterances → tools:**

| User says | Tool / action |
|-----------|----------------|
| “Give John OFF on the 15th” | `add_off_request(staff_id="John", date="2026-03-15")` or `add_manual_override(...)` |
| “Mark Sarah sick on March 10” | `add_manual_override(staff_id="Sarah", date="2026-03-10", status="S")` |
| “Public holiday for everyone on the 21st” | `add_manual_override_for_section(section="ALL", date="2026-03-21", status="PH")` |
| “What’s the min coverage for SERVERS?” | `get_coverage_config(section="SERVERS")` → agent explains |
| “Why did the solver fail?” | `get_solver_status()` / `get_last_warnings()` → agent explains in plain language |
| “Who’s working evening shift on Friday?” | `query_schedule(day="Friday", shift="D")` (if schedule already generated) |

**LangChain fit:** `create_tool_calling_agent` (or `create_react_agent`) with tools that read/write `st.session_state` or call your existing Python APIs (parser, config, optimizer). Streamlit can render the chat and pass messages to the agent.

**Scope:** Medium — define 5–8 tools, one agent, one chat UI.

---

### 2. Free-text → overrides & OFF requests (Structured output)

**Idea:** A text area where the manager pastes something like:

- *“PH on 21st for everyone. Sarah OFF 14th and 15th. Tom sick 10th. Maria vacation 18–20.”*

The LLM extracts structured data and we pre-fill the form (or apply via API).

**Output shape (e.g. Pydantic):**

```python
class ExtractedOverrides(BaseModel):
    manual_overrides: list[tuple[str, str, str]]   # (staff_id_or_section, date, code)
    off_requests: list[tuple[str, list[str]]]     # (staff_id, [dates])
```

**LangChain fit:** `llm.with_structured_output(ExtractedOverrides)` plus a prompt that includes staff names and section names from the current roster so the LLM can resolve “Sarah”, “SERVERS”, etc.

**Scope:** Small — one endpoint or Streamlit step, one model, validation before applying.

---

### 3. “Explain this schedule” / “Why this assignment?” (RAG or agent with context)

**Idea:** After generation, the user can ask:

- “Why is Alice on shift B this week?”
- “Why couldn’t you give John OFF on Tuesday?”

The system uses **context** (constraints, OFF-by-Wednesday rule, OFF requests, solver warnings) and optionally **RAG over a short “policy” doc** to generate a plain-language explanation.

**LangChain fit:**

- **Option A:** Agent with tools: `get_staff_assignments()`, `get_constraints()`, `get_off_requests()`, `get_warnings()` → LLM reasons and answers.
- **Option B:** RAG over a small doc (e.g. `context.md` section on rules) + current run context (constraints, warnings) injected into the prompt.

**Scope:** Medium — need to expose solver/run context as tool outputs or prompt context.

---

### 4. RAG over policy & roster format (RAG only)

**Idea:** In-app help: “What’s our OFF by Wednesday rule?”, “What do status codes PH, S, V mean?”, “What’s the roster Excel format?”

**Implementation:** Ingest **`docs/scheduling-rules.md` only** — a separate file that contains **only** scheduling rules and policy (shift slots, status codes, constraints, OFF by Wednesday, what the manager provides). Do **not** index `context.md` (project details, test status, paths, code). Chunk, embed, store in Chroma/FAISS. Retriever → prompt → answer in the UI.

**LangChain fit:** `RecursiveCharacterTextSplitter` → `OpenAIEmbeddings` (or another provider) → `Chroma` / `FAISS` → `RetrievalQA` or `ConversationalRetrievalChain` if you want follow-up questions.

**Scope:** Small — one rules-only doc, one retriever, one QA chain; no tools.

---

### 5. Smart defaults / recommendations (Structured output + chain)

**Idea:** Manager describes the week in natural language; the LLM suggests config.

- *“Quiet week, no events.”* → suggest fewer active slots, lower min coverage.
- *“Big event Friday evening, full house.”* → suggest slots C/D/E, higher SERVER min per day.

**Output:** Suggested `active_shift_slots`, `section_min_per_day` (and maybe `section_max_off_per_day`) that the user can accept or edit.

**LangChain fit:** Prompt + `with_structured_output(RecommendedConfig)` (Pydantic). Optional second step: “Here’s what I suggest … confirm?” (chain).

**Scope:** Small–medium — depends how much you want to refine the prompt and schema.

---

### 6. Conversational setup wizard (Structured output)

**Idea:** Instead of only forms, the user can type: *“We’re White Robata KSA, week starts Sunday, publish Saturday, OFF requests by Friday.”* The LLM fills setup fields (restaurant name, week_start_day, publish_day, off_request_deadline).

**LangChain fit:** Single shot `with_structured_output(SetupIntent)` + validation and pre-fill of the existing setup form.

**Scope:** Small — one extraction step, wire to existing wizard state.

---

### 7. Schedule comparison / “What changed?” (Agent or chain + diff)

**Idea:** User uploads or selects “previous week” schedule and “this week” schedule. Ask: “What changed?” or “Who gained/lost evenings?”

**Implementation:** Diff the two schedules (e.g. pandas or custom comparison), produce a structured summary; LLM turns it into a short narrative.

**LangChain fit:** Not necessarily RAG; a chain that takes “diff summary” as input and generates a readable report. Could be an agent if you add tools (e.g. “highlight only SERVER changes”).

**Scope:** Medium — need to define “previous schedule” (file upload vs stored run) and diff format.

---

## Suggested order of implementation

| Priority | Feature | LangChain pieces | Effort |
|----------|---------|------------------|--------|
| 1 | **Free-text → overrides (2)** | Structured output, one prompt | Small |
| 2 | **RAG over policy (4)** | Doc loader, splitter, vector store, RetrievalQA | Small |
| 3 | **Schedule assistant (1)** | Agent + 5–8 tools, chat UI | Medium |
| 4 | **Explain schedule (3)** | Agent with context tools or RAG + context | Medium |
| 5 | **Smart defaults (5)** | Structured output, optional chain | Small–Medium |
| 6 | **Conversational setup (6)** | Structured output | Small |
| 7 | **Schedule comparison (7)** | Chain + diff input | Medium |

---

## Technical notes

- **Provider:** Start with one LLM (e.g. `langchain_anthropic.ChatAnthropic` or `langchain_openai.ChatOpenAI`). LangChain makes it easy to swap later.
- **State:** Tools for the assistant should read/write the same state your app uses (e.g. `st.session_state`, or a small API layer over config/roster/schedule).
- **Safety:** For overrides and OFF requests, always show the user what was extracted and require confirmation before applying (no silent writes).
- **Cost:** Use structured output and short prompts where possible; reserve long context for “explain” and RAG.

---

## Next step

Pick one feature to implement first (recommended: **Free-text → overrides** or **RAG over policy**). From there we can outline exact prompts, tool schemas, and where to plug into `app.py` and the schedule form.
