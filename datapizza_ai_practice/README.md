# datapizza-ai Practice Examples

Ready-to-run examples for the `datapizza-ai` library, organized by topic from basic to advanced.

## Table of Contents

| Folder | What it covers |
|---|---|
| `01_clients/` | Create LLM clients (OpenAI, Google, Ollama) and stream responses |
| `02_basics/` | Structured output, multimodal input (images), conversation memory |
| `03_tools_and_agents/` | Define tools, build agents, web search |
| `04_pipelines/` | Pipeline components, dependencies, branching, foreach loops |
| `05_rag/` | Document ingestion and RAG query pipeline with Qdrant + Cohere |
| `06_multi_agent/` | Multi-agent orchestration (tech lead + data engineer + data scientist) |

## Prerequisites

1. **Python packages** -- install from the repo root:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables** -- create a `.env` file at the repo root:
   ```
   OPENAI_API_KEY=...
   GOOGLE_API_KEY=...
   COHERE_API_KEY=...
   COHERE_ENDPOINT=...
   QDRANT_HOST=localhost
   QDRANT_API_KEY=...
   ```

3. **Qdrant** (for RAG examples only):
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

4. **Ollama** (optional, for `01_clients/ollama.py`):
   ```bash
   ollama pull gemma3:4b
   ```

## Quick Start

Run any script from the **repo root**:

```bash
python datapizza_ai_practice/01_clients/client_factory.py
python datapizza_ai_practice/03_tools_and_agents/basic_agent.py
python datapizza_ai_practice/05_rag/rag_pipeline.py
```

## Hackathon Cheat Sheet

| I want to... | Look at |
|---|---|
| Call an LLM with one line | `01_clients/client_factory.py` |
| Use a local model (Ollama) | `01_clients/ollama.py` |
| Stream tokens to the terminal | `01_clients/streaming_response.py` |
| Get JSON/typed output from an LLM | `02_basics/structured_response.py` |
| Send an image to the LLM | `02_basics/multimodality.py` |
| Build a chatbot with memory | `02_basics/memory.py` |
| Define a custom tool | `03_tools_and_agents/tool_basics.py` |
| Create an autonomous agent | `03_tools_and_agents/basic_agent.py` |
| Give an agent web search | `03_tools_and_agents/websearch_agent.py` |
| Build a data-processing pipeline | `04_pipelines/components.py` + `branching.py` |
| Fan-out over a list (foreach) | `04_pipelines/loops.py` |
| Ingest PDFs into a vector store | `05_rag/ingestion_pipeline.py` |
| Ask questions over documents (RAG) | `05_rag/rag_pipeline.py` |
| Orchestrate multiple agents | `06_multi_agent/workflow.py` |
