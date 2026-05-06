# Test Instructions

## Bước 1: Kiểm tra Environment Variables

Đảm bảo file `.env` có đầy đủ các keys:

```bash
# Required
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...

# Required for tracing
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# Optional
OPENAI_MODEL=gpt-4o-mini
MAX_ITERATIONS=10
TIMEOUT_SECONDS=120
```

## Bước 2: Install Dependencies

```bash
pip install -e ".[llm]"
```

Hoặc install từng package:

```bash
pip install openai tavily-python langfuse langgraph tenacity
```

## Bước 3: Test Components

Chạy test đơn giản để kiểm tra từng component:

```bash
python test_simple.py
```

Kết quả mong đợi:
- ✓ Config loaded
- ✓ LLM Client works (test completion)
- ✓ Search Client works (test search)
- ✓ Langfuse Tracing enabled

## Bước 4: Test Full Workflow

Chạy full multi-agent workflow:

```bash
python t.py
```

File `t.py` sẽ:
1. Chạy multi-agent workflow với query: "What is GraphRAG and how does it work?"
2. Hiển thị kết quả từng bước
3. Hiển thị metrics (tokens, cost, latency)
4. Hiển thị Trace URL để xem trên Langfuse

## Bước 5: Kiểm tra Langfuse Dashboard

1. Mở Trace URL từ output của `t.py`
2. Hoặc vào https://cloud.langfuse.com
3. Kiểm tra:
   - Trace có hiển thị không?
   - Có thấy các spans: supervisor, researcher, analyst, writer không?
   - Có thấy LLM calls với tokens và cost không?

## Bước 6: Test CLI Commands

### Test Baseline:
```bash
python -m multi_agent_research_lab.cli baseline --query "What is machine learning?"
```

### Test Multi-Agent:
```bash
python -m multi_agent_research_lab.cli multi-agent --query "What is machine learning?"
```

### Test Benchmark:
```bash
python -m multi_agent_research_lab.cli benchmark --query "What is AI?" --query "What is ML?"
```

Benchmark report sẽ được lưu vào `reports/benchmark_report.md`

## Troubleshooting

### Error: "OPENAI_API_KEY not configured"
- Kiểm tra file `.env` có key không
- Kiểm tra key có đúng format không (bắt đầu bằng `sk-`)

### Error: "TAVILY_API_KEY not configured"
- Kiểm tra file `.env` có key không
- Lấy key tại: https://tavily.com

### Warning: "Langfuse tracing is DISABLED"
- Kiểm tra `LANGFUSE_PUBLIC_KEY` và `LANGFUSE_SECRET_KEY` trong `.env`
- Lấy keys tại: https://cloud.langfuse.com

### Error: "Module not found"
- Chạy: `pip install -e ".[llm]"`
- Hoặc install từng package riêng

### Langfuse không hiển thị trace
- Đợi vài giây rồi refresh
- Kiểm tra keys có đúng không
- Kiểm tra `LANGFUSE_HOST` có đúng không

## Customize Test Query

Để test với query khác, sửa trong file `t.py`:

```python
TEST_QUERY = "Your custom query here"
```

Sau đó chạy lại:

```bash
python t.py
```
