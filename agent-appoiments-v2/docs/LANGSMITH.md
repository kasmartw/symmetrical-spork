# LangSmith Tracing Guide

## Setup

1. Get API Key from [LangSmith](https://smith.langchain.com/)
2. Add to `.env`:
   ```bash
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_key
   LANGCHAIN_PROJECT=appointment-agent-v1.2
   ```

3. Run agent - traces auto-upload

## View Traces

Go to: https://smith.langchain.com/

## What You'll See

- **Full conversation flow**: Every node execution
- **Timing**: Time between nodes (identify bottlenecks)
- **Tool calls**: Which tools were called, inputs/outputs
- **LLM calls**: Prompts, responses, token usage
- **Errors**: Full stack traces

## Performance Analysis

Look for:
- Slow nodes (> 1s execution)
- Redundant tool calls
- Excessive LLM calls
- Long wait times between nodes

## Cost Tracking

LangSmith shows:
- Token usage per run
- Cost per conversation
- Cost trends over time
