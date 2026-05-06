# Lab 20: Multi-Agent Research System

Hệ thống nghiên cứu đa agent hoàn chỉnh với **Supervisor + Researcher + Analyst + Writer**, tích hợp Langfuse tracing và benchmark system.

> **Status**: ✅ Đã hoàn thành đầy đủ tất cả yêu cầu chức năng. Hệ thống production-ready với retry logic, fallback strategies, và comprehensive error handling.

## Implementation Status

### ✅ Hoàn thành (100%)

| Component | Status | File |
|---|:---:|---|
| LLM Client với OpenAI | ✅ | `services/llm_client.py` |
| Search Client với Tavily | ✅ | `services/search_client.py` |
| Supervisor Routing Logic | ✅ | `agents/supervisor.py` |
| Researcher Agent | ✅ | `agents/researcher.py` |
| Analyst Agent | ✅ | `agents/analyst.py` |
| Writer Agent | ✅ | `agents/writer.py` |
| LangGraph Workflow | ✅ | `graph/workflow.py` |
| Langfuse Tracing | ✅ | `observability/tracing.py` |
| Benchmark System | ✅ | `evaluation/benchmark.py` |
| Baseline Single-Agent | ✅ | `cli.py` |
| Guardrails & Error Handling | ✅ | Tất cả agents |
| CLI Commands | ✅ | `cli.py` |

### 🎯 Features

- ✅ Multi-agent workflow với conditional routing
- ✅ Single-agent baseline để so sánh
- ✅ Langfuse tracing với cost tracking
- ✅ Comprehensive benchmark metrics
- ✅ Retry logic với exponential backoff
- ✅ Graceful degradation khi agent fail
- ✅ Max iterations và timeout guards
- ✅ Error accumulation và reporting

## Learning outcomes

Sau 2 giờ lab, học viên cần có thể:

1. Thiết kế role rõ ràng cho nhiều agent.
2. Xây dựng shared state đủ thông tin cho handoff.
3. Thêm guardrail tối thiểu: max iterations, timeout, retry/fallback, validation.
4. Trace được luồng chạy và giải thích agent nào làm gì.
5. Benchmark single-agent vs multi-agent theo quality, latency, cost.

## Architecture mục tiêu

```text
User Query
   |
   v
Supervisor / Router
   |------> Researcher Agent  -> research_notes
   |------> Analyst Agent     -> analysis_notes
   |------> Writer Agent      -> final_answer
   |
   v
Trace + Benchmark Report
```

## System Architecture

### High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                    (CLI / API / Notebook)                        │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Workflow Orchestrator                       │
│                        (LangGraph)                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    Supervisor Agent                       │  │
│  │  • Routing Logic                                          │  │
│  │  • Max Iterations Guard                                   │  │
│  │  • State Management                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             │                                    │
│         ┌───────────────────┼───────────────────┐               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │ Researcher  │    │  Analyst    │    │   Writer    │        │
│  │   Agent     │    │   Agent     │    │   Agent     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
└─────────────────────────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  LLM Service    │  │ Search Service  │  │ Trace Service   │
│   (OpenAI)      │  │   (Tavily)      │  │  (Langfuse)     │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### Agent Architecture Details

#### 1. Supervisor Agent (Router)

**Responsibility**: Điều phối workflow và quyết định agent nào chạy tiếp theo

**Routing Logic**:
```python
if state.final_answer is not None:
    route = "done"
elif state.research_notes is None:
    route = "researcher"
elif state.analysis_notes is None:
    route = "analyst"
elif state.final_answer is None:
    route = "writer"
```

**Guardrails**:
- Max iterations check (default: 10)
- Route history tracking
- Error accumulation

**Input**: ResearchState
**Output**: ResearchState với updated route_history

---

#### 2. Researcher Agent

**Responsibility**: Tìm kiếm thông tin và tạo research notes

**Workflow**:
```text
1. Search Query → Tavily API
2. Get Sources (title, url, snippet)
3. Summarize Sources → LLM
4. Update state.sources + state.research_notes
```

**Key Features**:
- Retry logic: 3 attempts với exponential backoff
- Timeout: 30s per API call
- Graceful degradation: Continue với empty sources nếu search fail

**Input**: 
- `state.request.query`
- `state.request.max_sources`

**Output**:
- `state.sources`: List[SourceDocument]
- `state.research_notes`: str

**Error Handling**:
```python
try:
    sources = search_client.search(query, max_results)
    research_notes = llm_client.complete(summarize_prompt)
except SearchError:
    state.errors.append("Search failed")
    state.research_notes = "Research failed due to search error."
```

---

#### 3. Analyst Agent

**Responsibility**: Phân tích research notes và đánh giá sources

**Workflow**:
```text
1. Read research_notes + sources
2. Analyze → LLM:
   - Compare viewpoints
   - Assess credibility
   - Identify weak evidence
   - Highlight key insights
3. Update state.analysis_notes
```

**Key Features**:
- Critical analysis với multiple perspectives
- Source credibility assessment
- Gap identification

**Input**:
- `state.research_notes`
- `state.sources`

**Output**:
- `state.analysis_notes`: str

**Error Handling**:
```python
if not state.research_notes:
    state.errors.append("No research notes to analyze")
    state.analysis_notes = "No research notes available."
```

---

#### 4. Writer Agent

**Responsibility**: Tổng hợp thông tin và viết final answer với citations

**Workflow**:
```text
1. Read research_notes + analysis_notes + sources
2. Write Final Answer → LLM:
   - Synthesize information
   - Add citations [1], [2], etc.
   - Format for target audience
3. Update state.final_answer
```

**Key Features**:
- Citation formatting
- Audience-aware writing
- Comprehensive synthesis

**Input**:
- `state.research_notes`
- `state.analysis_notes`
- `state.sources`
- `state.request.audience`

**Output**:
- `state.final_answer`: str với citations

**Citation Format**:
```text
GraphRAG is a retrieval-augmented generation approach [1]. 
It uses knowledge graphs to improve context [2].

Sources:
[1] Microsoft Research: GraphRAG Overview
[2] ArXiv: Knowledge Graph RAG
```

---

### Shared State (ResearchState)

**Core Fields**:
```python
class ResearchState(TypedDict):
    # Input
    request: ResearchQuery          # User query + config
    
    # Agent Outputs
    sources: List[SourceDocument]   # From Researcher
    research_notes: Optional[str]   # From Researcher
    analysis_notes: Optional[str]   # From Analyst
    final_answer: Optional[str]     # From Writer
    
    # Workflow Control
    iteration: int                  # Current iteration count
    route_history: List[str]        # ["researcher", "analyst", "writer"]
    
    # Observability
    agent_results: List[AgentResult]  # Metadata per agent
    errors: List[str]                 # Accumulated errors
    trace_id: Optional[str]           # Langfuse trace ID
```

**State Transitions**:
```text
Initial State:
  iteration=0, route_history=[], all outputs=None

After Researcher:
  sources=[...], research_notes="...", route_history=["researcher"]

After Analyst:
  analysis_notes="...", route_history=["researcher", "analyst"]

After Writer:
  final_answer="...", route_history=["researcher", "analyst", "writer"]

Final State:
  route_history=[..., "done"], iteration=3
```

---

### Service Layer

#### LLM Client (OpenAI)

**Features**:
- Model: gpt-4o-mini (configurable)
- Retry: 3 attempts, exponential backoff
- Timeout: 30s per call
- Cost tracking: $0.15/1M input, $0.60/1M output tokens

**Interface**:
```python
def complete(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> LLMResponse:
    # Returns: content, input_tokens, output_tokens, cost_usd, latency
```

#### Search Client (Tavily)

**Features**:
- Search depth: advanced
- Retry: 3 attempts, exponential backoff
- Timeout: 30s per call
- Max results: configurable (default: 5)

**Interface**:
```python
def search(
    query: str,
    max_results: int = 5
) -> List[SourceDocument]:
    # Returns: title, url, snippet, metadata
```

#### Trace Client (Langfuse)

**Features**:
- Automatic span creation per agent
- LLM call tracking với tokens + cost
- Public trace URLs
- Cost aggregation

**Integration**:
```python
@observe(name="agent_name", as_type="span")
def run(self, state):
    with langfuse_client.start_as_current_observation(
        name="llm_call",
        as_type="generation"
    ) as generation_span:
        response = llm_client.complete(...)
        generation_span.update(
            output=response.content,
            usage_details={"input": ..., "output": ..., "total": ...},
            cost_details={"total": response.cost_usd}
        )
```

---

### Workflow Execution Flow

```text
1. User submits query
   ↓
2. Create initial ResearchState
   ↓
3. Supervisor: route = "researcher"
   ↓
4. Researcher Agent:
   - Search Tavily
   - Summarize with LLM
   - Update state
   ↓
5. Supervisor: route = "analyst"
   ↓
6. Analyst Agent:
   - Analyze research_notes
   - Update state
   ↓
7. Supervisor: route = "writer"
   ↓
8. Writer Agent:
   - Write final_answer
   - Update state
   ↓
9. Supervisor: route = "done"
   ↓
10. Return final ResearchState
    ↓
11. Display results + trace URL
```

**Conditional Routing**:
- LangGraph conditional edges based on `state.route_history[-1]`
- Each worker agent returns to Supervisor
- Supervisor decides next step or "done"

---

### Comparison: Single-Agent vs Multi-Agent

| Aspect | Single-Agent | Multi-Agent |
|---|---|---|
| **Architecture** | 1 LLM call | 3+ LLM calls |
| **Prompt** | Monolithic | Specialized per agent |
| **Latency** | Lower (~5-10s) | Higher (~15-30s) |
| **Cost** | Lower (~$0.01) | Higher (~$0.03-0.05) |
| **Quality** | Good | Better (specialized) |
| **Debuggability** | Hard | Easy (per-agent traces) |
| **Scalability** | Limited | High (add more agents) |
| **Use Case** | Simple queries | Complex research |

## Cấu trúc repo

```text
.
├── src/multi_agent_research_lab/
│   ├── agents/              # Agent interfaces + skeletons
│   ├── core/                # Config, state, schemas, errors
│   ├── graph/               # LangGraph workflow skeleton
│   ├── services/            # LLM, search, storage clients
│   ├── evaluation/          # Benchmark/evaluation skeleton
│   ├── observability/       # Logging/tracing hooks
│   └── cli.py               # CLI entrypoint
├── configs/                 # YAML configs for lab variants
├── docs/                    # Lab guide, rubric, design notes
├── tests/                   # Unit tests for skeleton behavior
├── notebooks/               # Optional notebook entrypoint
├── scripts/                 # Helper scripts
├── .env.example             # Environment variables template
├── pyproject.toml           # Python project config
├── Dockerfile               # Containerized dev/runtime
└── Makefile                 # Common commands
```

## Quickstart

### 1. Tạo môi trường

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e "[dev]"
cp .env.example .env
```

### 2. Cấu hình API keys

Mở `.env` và điền các API keys cần thiết:

```bash
# Required - OpenAI API
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Required - Tavily Search API
TAVILY_API_KEY=tvly-...

# Required - Langfuse Tracing
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional - System Configuration
MAX_ITERATIONS=10
TIMEOUT_SECONDS=120
LOG_LEVEL=INFO
```

**Lấy API keys:**
- OpenAI: https://platform.openai.com/api-keys
- Tavily: https://tavily.com (free tier: 1000 requests/month)
- Langfuse: https://cloud.langfuse.com (free tier available)

### 3. Chạy test đơn giản

```bash
# Test từng component
python test_simple.py

# Kết quả mong đợi:
# ✓ Config loaded
# ✓ LLM Client works
# ✓ Search Client works
# ✓ Langfuse Tracing enabled
```

### 4. Chạy full workflow

```bash
# Test multi-agent workflow
python t.py

# Hoặc dùng CLI
python -m multi_agent_research_lab.cli multi-agent \
  --query "What is GraphRAG and how does it work?"
```

### 5. Chạy baseline để so sánh

```bash
python -m multi_agent_research_lab.cli baseline \
  --query "What is GraphRAG and how does it work?"
```

### 6. Chạy benchmark

```bash
python -m multi_agent_research_lab.cli benchmark \
  --query "What is AI?" \
  --query "What is machine learning?" \
  --output reports/benchmark_report.md
```

## Milestones trong 2 giờ lab

| Thời lượng | Milestone | File gợi ý |
|---:|---|---|
| 0-15' | Setup, chạy baseline skeleton | `cli.py`, `services/llm_client.py` |
| 15-45' | Build Supervisor / router | `agents/supervisor.py`, `graph/workflow.py` |
| 45-75' | Thêm Researcher, Analyst, Writer | `agents/*.py`, `core/state.py` |
| 75-95' | Trace + benchmark single vs multi | `observability/tracing.py`, `evaluation/benchmark.py` |
| 95-115' | Peer review theo rubric | `docs/peer_review_rubric.md` |
| 115-120' | Exit ticket | `docs/lab_guide.md` |

## Quy ước production trong repo

- Tách rõ `agents`, `services`, `core`, `graph`, `evaluation`, `observability`.
- Không hard-code API key trong code.
- Tất cả input/output chính dùng Pydantic schema.
- Có type hints, linting, formatting, unit test tối thiểu.
- Có logging/tracing hook ngay từ đầu.
- Không để agent chạy vô hạn: dùng `max_iterations`, `timeout_seconds`.
- Có benchmark report thay vì chỉ demo output đẹp.

## Fallback Strategies & Error Handling

Hệ thống được thiết kế với nhiều lớp bảo vệ để đảm bảo robustness và reliability trong production.

### 1. Retry với Exponential Backoff

**LLM Client** (`services/llm_client.py`):
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Timeout, APIError))
)
def complete(self, ...):
    # Retry 3 lần với backoff: 1s, 2s, 4s
    # Timeout: 30 giây per call
```

**Search Client** (`services/search_client.py`):
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((Exception,))
)
def search(self, ...):
    # Retry 3 lần với backoff: 1s, 2s, 4s
    # Timeout: 30 giây per call
```

**Lý do**: API calls có thể fail tạm thời do network issues, rate limits, hoặc server overload. Exponential backoff giúp tránh overwhelm server và tăng success rate.

### 2. Graceful Degradation

Khi một agent fail, workflow vẫn tiếp tục thay vì crash hoàn toàn:

**Researcher Agent fails**:
```python
except SearchError as e:
    state.errors.append(f"Researcher search failed: {str(e)}")
    state.research_notes = "Research failed due to search error."
    # Workflow tiếp tục, Analyst và Writer sẽ làm việc với empty data
```

**Analyst Agent fails**:
```python
except Exception as e:
    state.errors.append(f"Analyst failed: {str(e)}")
    state.analysis_notes = "Analysis failed due to error."
    # Writer vẫn có thể dùng research_notes để tạo answer
```

**Writer Agent fails**:
```python
except Exception as e:
    state.errors.append(f"Writer failed: {str(e)}")
    state.final_answer = "Unable to generate answer due to error."
    # Trả về partial result với error message
```

**Lý do**: Trong production, một phần kết quả vẫn tốt hơn là không có gì. User có thể retry hoặc điều chỉnh query dựa trên error message.

### 3. Timeout Protection

**Per API Call Timeout**:
- LLM Client: 30 giây per completion
- Search Client: 30 giây per search
- Behavior: Raise TimeoutError sau khi retry hết

**Total Workflow Timeout**:
- Default: 120 giây (configurable via `TIMEOUT_SECONDS`)
- Implementation: Supervisor kiểm tra elapsed time
- Behavior: Dừng workflow, trả về partial results với error

**Lý do**: Ngăn workflow chạy vô hạn, đặc biệt quan trọng trong production với nhiều concurrent requests.

### 4. Max Iterations Guard

**Implementation** (`agents/supervisor.py`):
```python
if state.iteration >= settings.max_iterations:
    state.errors.append(f"Max iterations ({settings.max_iterations}) reached")
    state.record_route("done")
    return state
```

**Default**: 10 iterations (configurable via `MAX_ITERATIONS`)

**Lý do**: Ngăn infinite loops nếu routing logic có bug hoặc agents không produce expected output.

### 5. State Validation

**Pydantic Schema Validation**:
- ResearchState được validate tự động sau mỗi agent execution
- Type checking cho tất cả fields
- Automatic error nếu data không hợp lệ

**Agent Output Validation**:
```python
if not state.research_notes:
    state.errors.append("Researcher: No research notes to analyze")
    state.analysis_notes = "No research notes available for analysis."
```

**Lý do**: Đảm bảo data consistency và catch bugs sớm trong development.

### 6. Error Accumulation

**Pattern**:
```python
state.errors.append(f"Agent X failed: {error_message}")
# Workflow tiếp tục
# Tất cả errors được collect và report ở cuối
```

**Benefits**:
- Không mất thông tin về failures
- User thấy được toàn bộ vấn đề, không chỉ error đầu tiên
- Dễ debug và improve system

### 7. Cost Tracking & Monitoring

**Langfuse Integration**:
```python
generation_span.update(
    output=llm_response.content,
    usage_details={
        "input": llm_response.input_tokens,
        "output": llm_response.output_tokens,
        "total": llm_response.input_tokens + llm_response.output_tokens
    },
    cost_details={
        "total": llm_response.cost_usd  # Tracked per generation
    }
)
```

**Cost Calculation** (`services/llm_client.py`):
```python
# gpt-4o-mini pricing
input_cost = response.usage.prompt_tokens * 0.15 / 1_000_000
output_cost = response.usage.completion_tokens * 0.60 / 1_000_000
total_cost = input_cost + output_cost
```

**Lý do**: Cost visibility là critical trong production. Langfuse dashboard hiển thị cost per trace, giúp optimize và budget planning.

### 8. Failure Mode Examples

**Scenario 1: Tavily API Down**
- Researcher retry 3 lần → fail
- Error logged: "Researcher search failed: Tavily API timeout"
- Analyst nhận empty sources → tạo analysis note về missing data
- Writer tạo answer với disclaimer về limited information
- **Result**: Partial answer với clear error message

**Scenario 2: OpenAI Rate Limit**
- LLM Client retry 3 lần với exponential backoff
- Nếu vẫn fail → error logged
- Workflow dừng ở agent hiện tại
- **Result**: Partial results với error về rate limit

**Scenario 3: Infinite Loop Bug**
- Supervisor routing sai → agents chạy lặp lại
- Max iterations guard kick in sau 10 iterations
- Workflow dừng với error: "Max iterations reached"
- **Result**: Partial results, developer được alert về bug

### 9. Monitoring & Observability

**Langfuse Tracing**:
- Mỗi agent execution = 1 span
- Mỗi LLM call = 1 generation với tokens + cost
- Routing decisions được log
- Trace URL available sau mỗi run

**Metrics Tracked**:
- Latency per agent
- Token usage per agent
- Cost per agent
- Error rate
- Citation coverage
- Quality score

**Access Traces**:
```bash
# Sau khi chạy workflow
python t.py
# Output sẽ có: Trace URL: https://cloud.langfuse.com/trace/{trace_id}
```

### 10. Best Practices Implemented

✅ **Separation of Concerns**: Mỗi agent có responsibility rõ ràng
✅ **Fail Fast**: Validate input sớm, raise errors rõ ràng
✅ **Fail Safe**: Graceful degradation thay vì crash
✅ **Observability**: Comprehensive logging và tracing
✅ **Cost Awareness**: Track và report cost cho mỗi operation
✅ **Testability**: Mỗi component có thể test độc lập
✅ **Configuration**: Tất cả thresholds configurable via env vars
✅ **Documentation**: Inline comments và type hints đầy đủ

## Benchmark Results

Hệ thống tự động so sánh single-agent vs multi-agent theo các metrics:

| Metric | Description | Calculation |
|---|---|---|
| **Latency** | Thời gian thực thi (giây) | Wall-clock time |
| **Cost** | Chi phí API calls (USD) | Token usage × pricing |
| **Quality** | Điểm chất lượng (0-10) | Rubric-based scoring |
| **Citation Coverage** | % sources được cite | Cited sources / Total sources |
| **Error Rate** | Tỷ lệ lỗi | Failed queries / Total queries |

**Chạy benchmark**:
```bash
python -m multi_agent_research_lab.cli benchmark \
  --query "What is AI?" \
  --query "What is ML?" \
  --query "What is GraphRAG?" \
  --output reports/benchmark_report.md
```

**Expected Trade-offs**:
- Multi-agent: Higher quality, higher cost, higher latency
- Single-agent: Lower cost, lower latency, lower quality
- Use case dependent: Chọn approach phù hợp với requirements

## Troubleshooting

### Error: "OPENAI_API_KEY not configured"
```bash
# Kiểm tra .env file
cat .env | grep OPENAI_API_KEY

# Đảm bảo key bắt đầu bằng "sk-"
OPENAI_API_KEY=sk-...
```

### Error: "TAVILY_API_KEY not configured"
```bash
# Lấy free API key tại https://tavily.com
# Add vào .env
TAVILY_API_KEY=tvly-...
```

### Warning: "Langfuse tracing is DISABLED"
```bash
# Kiểm tra Langfuse keys
cat .env | grep LANGFUSE

# Cần cả 3 keys:
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Langfuse không hiển thị cost
- ✅ **Fixed**: Đã cập nhật code để dùng đúng format `cost_details={"total": cost}`
- Langfuse cần key `"total"` chứ không phải `"total_cost"`
- Xem commit history để biết chi tiết fix

### Module not found errors
```bash
# Reinstall dependencies
pip install -e ".[llm]"

# Hoặc install từng package
pip install openai tavily-python langfuse langgraph tenacity
```

## TODO chính cho học viên

~~Tìm trong code các marker:~~

```bash
grep -R "TODO(student)" -n src tests docs
```

~~Các phần học viên cần tự làm:~~

~~1. Implement LLM client.~~
~~2. Implement web/search client hoặc mock search source.~~
~~3. Implement routing decision trong Supervisor.~~
~~4. Implement từng worker agent.~~
~~5. Build LangGraph workflow.~~
~~6. Thêm tracing provider thật: LangSmith, Langfuse hoặc OpenTelemetry.~~
~~7. Viết benchmark report.~~

**✅ Update**: Tất cả đã được implement đầy đủ. Không còn TODO nào cần làm.

## Deliverables

### 1. GitHub Repository
- ✅ Code hoàn chỉnh với tất cả agents implemented
- ✅ README với fallback strategies documentation
- ✅ Configuration files (.env.example)
- ✅ Test files (test_simple.py, t.py)

### 2. Langfuse Trace
- ✅ Screenshot hoặc public trace URL
- ✅ Hiển thị đầy đủ: agents, LLM calls, tokens, cost
- ✅ Routing decisions visible

**Ví dụ trace URL**: `https://cloud.langfuse.com/trace/{trace_id}`

### 3. Benchmark Report
- ✅ File: `reports/benchmark_report.md`
- ✅ So sánh single-agent vs multi-agent
- ✅ Metrics: latency, cost, quality, citations
- ✅ Analysis và recommendations

### 4. Failure Modes Documentation
Xem section **Fallback Strategies & Error Handling** ở trên, bao gồm:
- Retry logic với exponential backoff
- Graceful degradation patterns
- Timeout protection
- Max iterations guard
- Error accumulation
- 3 failure mode examples với expected behavior

## Project Structure Details

```text
src/multi_agent_research_lab/
├── agents/
│   ├── base.py              # Base agent interface
│   ├── supervisor.py        # ✅ Routing logic với max iterations guard
│   ├── researcher.py        # ✅ Search + summarize với retry
│   ├── analyst.py           # ✅ Analysis với error handling
│   ├── writer.py            # ✅ Final answer với citations
│   └── critic.py            # Optional (not required)
├── core/
│   ├── config.py            # Settings từ env vars
│   ├── state.py             # ResearchState với Pydantic validation
│   ├── schemas.py           # Data models
│   └── errors.py            # Custom exceptions
├── graph/
│   └── workflow.py          # ✅ LangGraph với conditional routing
├── services/
│   ├── llm_client.py        # ✅ OpenAI với retry + timeout
│   ├── search_client.py     # ✅ Tavily với retry + timeout
│   └── storage.py           # Optional storage
├── evaluation/
│   ├── benchmark.py         # ✅ Metrics calculation
│   └── report.py            # ✅ Markdown report generation
├── observability/
│   ├── logging.py           # Structured logging
│   └── tracing.py           # ✅ Langfuse integration
└── cli.py                   # ✅ CLI với baseline, multi-agent, benchmark
```

## Key Learnings & Best Practices

### When to Use Multi-Agent

✅ **Use Multi-Agent when**:
- Task requires specialized expertise (research, analysis, writing)
- Quality and depth are more important than speed
- Need clear separation of concerns for debugging
- Want to trace and optimize individual steps
- Complex reasoning requires multiple perspectives

❌ **Don't Use Multi-Agent when**:
- Simple tasks that one LLM call can handle
- Latency is critical (real-time responses)
- Cost is primary constraint
- Task doesn't benefit from specialization

### Design Principles Applied

1. **Clear Agent Responsibilities**
   - Researcher: Search + summarize sources
   - Analyst: Compare viewpoints + assess credibility
   - Writer: Synthesize + format with citations
   - Supervisor: Route based on state

2. **Shared State Pattern**
   - Single ResearchState passed through workflow
   - Each agent reads and writes specific fields
   - Immutable history (route_history, agent_results)
   - Error accumulation for debugging

3. **Fail-Safe Architecture**
   - Never crash on single agent failure
   - Always return partial results
   - Collect all errors for visibility
   - Graceful degradation over hard failures

4. **Observability First**
   - Trace every agent execution
   - Log every LLM call with tokens + cost
   - Track routing decisions
   - Measure end-to-end metrics

5. **Cost Awareness**
   - Track cost per agent
   - Compare single vs multi-agent cost
   - Optimize token usage
   - Make cost visible in traces

### Common Pitfalls Avoided

❌ **Infinite Loops**: Fixed with max_iterations guard
❌ **Hanging Workflows**: Fixed with timeout protection
❌ **Silent Failures**: Fixed with error accumulation
❌ **Missing Cost Data**: Fixed with proper Langfuse integration
❌ **Hard to Debug**: Fixed with comprehensive tracing
❌ **Brittle System**: Fixed with retry + fallback logic

## References

- Anthropic: Building effective agents — https://www.anthropic.com/engineering/building-effective-agents
- OpenAI Agents SDK orchestration/handoffs — https://developers.openai.com/api/docs/guides/agents/orchestration
- LangGraph concepts — https://langchain-ai.github.io/langgraph/concepts/
- LangSmith tracing — https://docs.smith.langchain.com/
- Langfuse tracing — https://langfuse.com/docs
- Langfuse cost tracking — https://langfuse.com/docs/model-usage-and-cost

---

**Author**: Multi-Agent Research Lab Team  
**Last Updated**: 2026-05-06  
**Status**: ✅ Production Ready  
**License**: MIT
