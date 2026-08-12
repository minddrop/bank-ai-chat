# Local LLM Development Environment Guide

## Overview

This guide details how developers can configure and run a **lightweight local LLM environment** (`Qwen2.5-0.5B`, `Qwen2.5-1.5B`, or `Gemma-2B`) for offline local development and testing of the Japanese Major Bank AI Customer Assistant.

*(See [ADR-0019](file:///home/joe/src/bank-ai-chat/docs/adr/0019-local-llm-provider-and-fallback-architecture.md) for architectural specifications and fallback design)*

> [!IMPORTANT]
> **Deployment Scope Note**: The local LLM environment is designed **EXCLUSIVELY for local offline development, prototyping, and test suite execution**. The local LLM system will **NOT** be deployed to AWS production environments (where Amazon Bedrock Nova Lite `amazon.nova-lite-v1:0` is deployed under FISC compliance per [ADR-0002](file:///home/joe/src/bank-ai-chat/docs/adr/0002-aws-bedrock-nova-lite-model-selection.md) and [ADR-0019](file:///home/joe/src/bank-ai-chat/docs/adr/0019-local-llm-provider-and-fallback-architecture.md)).

---

## 🚀 Recommended Light Local LLMs

For fast local Japanese text generation with minimal memory footprint (< 1 GB RAM), we recommend the following light open-weights models:

1. **`qwen2.5:0.5b`** (Recommended Default):
   - Memory footprint: ~390 MB RAM
   - Context window: 32k tokens
   - Japanese Keigo support: Excellent relative to size
2. **`qwen2.5:1.5b`**:
   - Memory footprint: ~980 MB RAM
   - High fidelity Japanese response generation
3. **`gemma:2b`**:
   - Memory footprint: ~1.4 GB RAM

---

## 🛠️ Setup Instructions (Using Ollama)

### 1. Install Ollama
Download and install Ollama for Linux / macOS / Windows from [https://ollama.com](https://ollama.com).

### 2. Pull Lightweight Model
Run the following command to download the 0.5B or 1.5B light model:
```bash
ollama pull qwen2.5:0.5b
```

### 3. Start Local Model Server
Ensure Ollama server is running (defaults to `http://localhost:11434`):
```bash
ollama serve
```

---

## 🔧 Configuring the Backend for Local LLM Mode

Set the environment variables before starting the FastAPI backend (`src/backend/app.py`):

```bash
# Enable Local LLM Provider Mode
export LLM_PROVIDER=local

# Set Local LLM Model and API URL
export LOCAL_LLM_MODEL=qwen2.5:0.5b
export LOCAL_LLM_URL=http://localhost:11434/v1

# Run the local backend
python3 src/backend/app.py
```

### Automatic Fallback Behavior
If Ollama or the local HTTP server is not active, `LocalLLMClient` automatically falls back to the internal **Local Light Development Engine**, allowing developers to build and test UI, RAG, and Control Plane pipelines with zero setup overhead.

---

## 🧪 Testing the Local LLM Setup

Run the helper script to verify your local LLM configuration:

```bash
python3 scripts/setup_local_llm.py --model qwen2.5:0.5b
```

Run the automated local test suite:
```bash
python3 -m unittest tests/test_local_llm.py
```
