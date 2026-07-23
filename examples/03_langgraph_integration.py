"""LangGraph integration via a Langfuse callback handler.

Builds a tiny two-node graph and runs it with the wrapper's callback handler attached, inside a
``trace_context`` that sets session/user/tags on the trace. Requires the ``langchain`` extra:

    pip install 'langfuse-wrapper[langchain]'
    python examples/03_langgraph_integration.py
"""

from __future__ import annotations

from typing import TypedDict

import langfuse_wrapper as lw


class State(TypedDict):
    question: str
    answer: str


def retrieve(state: State) -> dict[str, str]:
    return {"answer": f"context for {state['question']!r}"}


def respond(state: State) -> dict[str, str]:
    return {"answer": f"Answer using {state['answer']}"}


def main() -> None:
    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError:
        print("langgraph not installed. Install with: pip install 'langfuse-wrapper[langchain]'")
        return

    builder = StateGraph(State)
    builder.add_node("retrieve", retrieve)
    builder.add_node("respond", respond)
    builder.add_edge(START, "retrieve")
    builder.add_edge("retrieve", "respond")
    builder.add_edge("respond", END)
    graph = builder.compile()

    print(f"wrapper active: {lw.is_enabled()}")

    # get_handler() returns None when the wrapper is inactive, so this stays clean either way.
    handler = lw.get_handler()
    with lw.trace_context(session_id="graph-session", user_id="priyanshu", tags=["langgraph"]):
        result = graph.invoke(
            {"question": "What is CHAMP?"},
            config={"callbacks": [handler] if handler else []},
        )

    print("graph result:", result)
    lw.flush()
    print("done")


if __name__ == "__main__":
    main()
