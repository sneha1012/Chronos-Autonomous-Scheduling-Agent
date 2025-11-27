# 🚀 Chronos Quick Start Guide

Get Chronos up and running in 5 minutes!

## Prerequisites

- Python 3.10+
- GPU with 6GB+ VRAM (or CPU, but slower)
- HuggingFace account (for Llama 3 access)

## Installation

### Step 1: Clone and Setup

```bash
git clone https://github.com/yourusername/Chronos-Autonomous-Scheduling-Agent.git
cd Chronos-Autonomous-Scheduling-Agent
./scripts/setup.sh
```

### Step 2: Configure API Keys

Edit `.env` file:

```bash
# Required
HUGGINGFACE_TOKEN=hf_xxxxxxxxxxxxx

# Optional (for Gmail/Calendar features)
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_secret
```

**Get HuggingFace Token:**
1. Go to https://huggingface.co/settings/tokens
2. Create a new token with "read" access
3. Request access to Llama 3: https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct

### Step 3: Run Demo

```bash
source venv/bin/activate
python scripts/demo.py
```

## Usage Examples

### Option 1: Interactive CLI

```bash
python scripts/cli.py
```

Then type requests like:
- "Schedule a team meeting next Tuesday"
- "Find time for code review tomorrow"
- "What conflicts do I have next week?"

### Option 2: Python SDK

```python
from src.chronos.graph.workflow import create_workflow

workflow = create_workflow()
await workflow.initialize()

result = await workflow.run(
    user_request="Schedule a client demo next Monday at 2pm",
    calendar_events=[]  # Your calendar events here
)

print(result.final_response)
```

### Option 3: API Server

```bash
# Start server
python -m uvicorn src.chronos.api.app:app --reload

# Make request
curl -X POST http://localhost:8000/schedule \
  -H "Content-Type: application/json" \
  -d '{"request": "Schedule team meeting tomorrow"}'
```

## Optional: Gmail/Calendar Setup

To enable real Gmail and Calendar integration:

1. **Create Google Cloud Project**:
   - Go to https://console.cloud.google.com/
   - Create new project
   - Enable Gmail API and Calendar API

2. **Create OAuth Credentials**:
   - APIs & Services → Credentials
   - Create OAuth 2.0 Client ID
   - Download as `credentials.json` in project root

3. **First Run**:
   - Will open browser for OAuth consent
   - Grant calendar and Gmail permissions
   - Token saved automatically

## Troubleshooting

### Out of Memory

If you get CUDA OOM errors:

```python
# Edit src/chronos/config.py
model:
  load_in_4bit: True  # Enable quantization
```

### Slow Performance

Running on CPU? Expect 10x slower inference. Consider:
- Using smaller model (Llama 3.2 1B)
- Running on cloud GPU (Google Colab, RunPod)
- Using API-based model (OpenAI, Anthropic)

### Model Download Issues

```bash
# Pre-download model
from huggingface_hub import snapshot_download
snapshot_download("meta-llama/Meta-Llama-3-8B-Instruct")
```

## Next Steps

- Read full [README.md](README.md) for architecture details
- Check [LINKEDIN_STRATEGY.md](LINKEDIN_STRATEGY.md) for showcasing your work
- Explore code in `src/chronos/`
- Run tests: `pytest tests/`

## Support

- Issues: GitHub Issues
- Discussions: GitHub Discussions
- Email: your.email@example.com

Happy scheduling! 🎉

