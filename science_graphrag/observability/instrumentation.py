def setup_langchain_instrumentation() -> None:
    """Register OpenInference LangChain instrumentor with current OTel provider."""
    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor

        LangChainInstrumentor().instrument()
    except ImportError:
        # agent extra is optional in some environments
        return
