from langchain_core.messages import SystemMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from .llms import get_chat_model
from .prompts import SYSTEM_PROMPT
from .tools import build_tools


def build_chat_graph(user, conversation, *, streaming=False):
    tools = build_tools(user=user, conversation=conversation)
    model = get_chat_model(streaming=streaming).bind_tools(tools)

    def assistant_node(state: MessagesState):
        response = model.invoke([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
        return {"messages": [response]}

    graph = StateGraph(MessagesState)
    graph.add_node("assistant", assistant_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "assistant")
    graph.add_conditional_edges("assistant", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "assistant")
    return graph.compile()
