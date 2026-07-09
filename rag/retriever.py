import os
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import MarkdownHeaderTextSplitter

DOC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gold_causal_chain.md")
INDEX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "faiss_index")

_embeddings = None
_vectorstore = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        _embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    return _embeddings


def build_vectorstore():
    """Builds the FAISS index from gold_causal_chain.md, chunked by factor (## headers)."""
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    headers_to_split_on = [("##", "factor")]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks = splitter.split_text(text)

    embeddings = _get_embeddings()
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(INDEX_PATH)
    return vectorstore


def get_vectorstore():
    """Loads the FAISS index from disk, building it first if it doesn't exist yet."""
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    embeddings = _get_embeddings()
    if os.path.exists(INDEX_PATH):
        _vectorstore = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        _vectorstore = build_vectorstore()
    return _vectorstore


def retrieve_factor_context(factor_query: str, k: int = 1) -> str:
    """Retrieves the most relevant chunk(s) of the gold causal chain document for a given factor query, using MMR."""
    try:
        vectorstore = get_vectorstore()
        results = vectorstore.max_marginal_relevance_search(factor_query, k=k, fetch_k=9)
        return "\n\n".join([doc.page_content for doc in results])
    except Exception as e:
        return f"RAG context unavailable ({str(e)})"