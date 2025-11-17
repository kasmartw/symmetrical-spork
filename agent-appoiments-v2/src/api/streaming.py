"""Server-Sent Events streaming utilities."""
import json
import asyncio
from typing import AsyncGenerator, Dict, Any


async def stream_graph_events(
    graph,
    input_data: Dict[str, Any],
    config: Dict[str, Any]
) -> AsyncGenerator[str, None]:
    """
    Stream LangGraph execution as Server-Sent Events.

    Yields SSE-formatted events with:
    - chunk: Partial output from graph nodes
    - done: Boolean indicating completion
    - metadata: Additional context (node name, state, etc.)

    Args:
        graph: Compiled LangGraph instance
        input_data: Input dictionary for graph.astream()
        config: Configuration dict (thread_id, org_id, etc.)

    Yields:
        SSE-formatted strings: "data: {json}\n\n"
    """
    try:
        # Stream events from LangGraph
        async for event in graph.astream(input_data, config=config):
            # event structure: {node_name: {messages: [...], ...}}

            for node_name, node_output in event.items():
                # Extract relevant data from node output
                chunk_data = {
                    "chunk": str(node_output),
                    "done": False,
                    "metadata": {
                        "node": node_name,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                }

                # Format as SSE
                yield f"data: {json.dumps(chunk_data)}\n\n"

        # Send final "done" event
        final_event = {
            "chunk": "",
            "done": True,
            "metadata": {"completed": True}
        }
        yield f"data: {json.dumps(final_event)}\n\n"

    except Exception as e:
        # Send error event
        error_event = {
            "chunk": "",
            "done": True,
            "error": str(e)
        }
        yield f"data: {json.dumps(error_event)}\n\n"
