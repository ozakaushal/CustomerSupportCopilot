from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langgraph.graph import StateGraph, START, END
from app.core.config import get_settings
from app.rag.knowledge_base import search
from app.rag.prompts import (
    ROUTE_PROMPT, CHECK_KB_PROMPT, CHECK_WEB_PROMPT, REWRITE_PROMPT,
    ANSWER_KB_PROMPT, ANSWER_WEB_PROMPT, CHAT_PROMPT, NO_ANSWER,
)
from app.rag.state import CopilotState, RouteResult, CheckResult

settings = get_settings()

llm = None
web_search = None


# returns the groq chat model, creates it only once
def get_llm():
    global llm
    if llm is None:
        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is missing in .env")
        llm = ChatGroq(model=settings.chat_model, temperature=0, api_key=settings.groq_api_key)
    return llm


# returns the tavily web search tool, creates it only once
def get_web_search():
    global web_search
    if web_search is None:
        if not settings.tavily_api_key:
            raise RuntimeError("TAVILY_API_KEY is missing in .env")
        web_search = TavilySearch(tavily_api_key=settings.tavily_api_key, max_results=5, include_answer=True)
    return web_search


# joins the kb chunks into one text with file name on top of each
def make_kb_context(docs):
    text = ""
    for doc in docs:
        text += "[" + doc.metadata.get("source", "unknown") + "]\n" + doc.page_content + "\n\n"
    return text


# ---------- graph steps ----------

# checks if the question is IT related or just small talk
def classify(state):
    result = get_llm().with_structured_output(RouteResult).invoke(
        ROUTE_PROMPT.format(question=state["question"])
    )
    return {
        "answered_by": result.route,
        "steps": state["steps"] + ["Classified as: " + result.route],
    }


# searches our pinecone knowledge base
def search_kb(state):
    docs = search(state["search_query"])
    return {
        "kb_docs": docs,
        "steps": state["steps"] + [f"Knowledge base search: {len(docs)} chunks found"],
    }


# asks the llm if the kb results are good enough to answer
def check_kb(state):
    context = make_kb_context(state["kb_docs"])
    result = get_llm().with_structured_output(CheckResult).invoke(
        CHECK_KB_PROMPT.format(question=state["question"], context=context)
    )
    if result.enough:
        step = "Knowledge base results: enough"
    else:
        step = "Knowledge base results: not enough"
    return {"kb_ok": result.enough, "steps": state["steps"] + [step]}


# searches the internet using tavily
def search_web(state):
    result = get_web_search().invoke({"query": state["search_query"]})

    text = ""
    sources = []
    if isinstance(result, dict):
        if result.get("answer"):
            text += "Summary: " + result["answer"] + "\n\n"
        for item in result.get("results", []):
            text += item.get("title", "") + "\n" + item.get("url", "") + "\n" + item.get("content", "") + "\n\n"
            sources.append({"title": item.get("title") or item.get("url"), "url": item.get("url", ""), "kind": "web"})
    else:
        text = str(result)

    return {
        "web_context": text,
        "sources": sources,
        "steps": state["steps"] + [f"Web search: {len(sources)} results"],
    }


# asks the llm if the web results are good enough to answer
def check_web(state):
    result = get_llm().with_structured_output(CheckResult).invoke(
        CHECK_WEB_PROMPT.format(question=state["question"], context=state["web_context"])
    )
    if result.enough:
        step = "Web results: enough"
    else:
        step = "Web results: not enough"
    return {"web_ok": result.enough, "steps": state["steps"] + [step]}


# rewrites the question to get better search results next time
def rewrite(state):
    new_query = get_llm().invoke(REWRITE_PROMPT.format(question=state["question"])).content.strip()
    return {
        "search_query": new_query,
        "rewrites": state["rewrites"] + 1,
        "steps": state["steps"] + ["Rewrote question as: " + new_query],
    }


# writes the final answer from the kb chunks
def answer_from_kb(state):
    context = make_kb_context(state["kb_docs"])
    reply = get_llm().invoke(ANSWER_KB_PROMPT.format(question=state["question"], context=context))

    # list each file only once in sources
    sources = []
    file_names = []
    for doc in state["kb_docs"]:
        name = doc.metadata.get("source", "Knowledge base")
        if name not in file_names:
            file_names.append(name)
            sources.append({"title": name, "url": "", "kind": "kb"})

    return {
        "answer": reply.content,
        "answered_by": "knowledge_base",
        "sources": sources,
        "steps": state["steps"] + ["Answered from knowledge base"],
    }


# writes the final answer from the web results
def answer_from_web(state):
    reply = get_llm().invoke(ANSWER_WEB_PROMPT.format(question=state["question"], context=state["web_context"]))
    return {
        "answer": reply.content,
        "answered_by": "web",
        "steps": state["steps"] + ["Answered from web results"],
    }


# replies to hi / thanks type messages without any search
def small_talk(state):
    reply = get_llm().invoke(CHAT_PROMPT.format(question=state["question"]))
    return {
        "answer": reply.content,
        "answered_by": "chat",
        "steps": state["steps"] + ["Replied directly, no search needed"],
    }


# used when nothing worked, tells the user to raise a ticket
def give_up(state):
    return {
        "answer": NO_ANSWER,
        "answered_by": "none",
        "sources": [],
        "steps": state["steps"] + ["No proper answer found"],
    }


# ---------- decide next step ----------

# goes to kb search for IT questions, else small talk
def after_classify(state):
    if state["answered_by"] == "kb":
        return "search_kb"
    return "small_talk"


# answers from kb if results are good, else tries web
def after_check_kb(state):
    if state["kb_ok"]:
        return "answer_from_kb"
    return "search_web"


# answers from web if good, else rewrites the question or gives up
def after_check_web(state):
    if state["web_ok"]:
        return "answer_from_web"
    if state["rewrites"] < settings.max_rewrites:
        return "rewrite"
    return "give_up"


# ---------- build the graph ----------

# connects all the steps together into one langgraph flow
def build_graph():
    graph = StateGraph(CopilotState)

    graph.add_node("classify", classify)
    graph.add_node("search_kb", search_kb)
    graph.add_node("check_kb", check_kb)
    graph.add_node("search_web", search_web)
    graph.add_node("check_web", check_web)
    graph.add_node("rewrite", rewrite)
    graph.add_node("answer_from_kb", answer_from_kb)
    graph.add_node("answer_from_web", answer_from_web)
    graph.add_node("small_talk", small_talk)
    graph.add_node("give_up", give_up)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", after_classify, ["search_kb", "small_talk"])
    graph.add_edge("search_kb", "check_kb")
    graph.add_conditional_edges("check_kb", after_check_kb, ["answer_from_kb", "search_web"])
    graph.add_edge("search_web", "check_web")
    graph.add_conditional_edges("check_web", after_check_web, ["answer_from_web", "rewrite", "give_up"])
    graph.add_edge("rewrite", "search_kb")

    graph.add_edge("answer_from_kb", END)
    graph.add_edge("answer_from_web", END)
    graph.add_edge("small_talk", END)
    graph.add_edge("give_up", END)

    return graph.compile()


copilot = build_graph()


# runs the full graph for one question and returns the final state
def run_copilot(question):
    start_state = {
        "question": question,
        "search_query": question,
        "kb_docs": [],
        "web_context": "",
        "kb_ok": False,
        "web_ok": False,
        "rewrites": 0,
        "answer": "",
        "answered_by": "",
        "sources": [],
        "steps": [],
    }
    return copilot.invoke(start_state)
