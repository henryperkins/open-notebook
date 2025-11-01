import os
from typing import Any, Mapping, Optional, cast

from ai_prompter import Prompter
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from loguru import logger
from typing_extensions import TypedDict

from open_notebook.domain.notebook import Source
from open_notebook.domain.transformation import DefaultPrompts, Transformation
from open_notebook.exceptions import InvalidInputError
from open_notebook.graphs.utils import provision_langchain_model
from open_notebook.utils import clean_thinking_content, token_count


def _max_prompt_tokens() -> int:
    raw = os.getenv("TRANSFORMATION_MAX_PROMPT_TOKENS")
    fallback = 120_000
    if raw is None:
        return fallback
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError
        return value
    except ValueError:
        logger.warning(
            "Invalid TRANSFORMATION_MAX_PROMPT_TOKENS=%r; using %d." % (raw, fallback)
        )
        return fallback


MAX_PROMPT_TOKENS = _max_prompt_tokens()


class TransformationState(TypedDict):
    input_text: str
    source: Source
    transformation: Transformation
    output: str


async def run_transformation(
    state: Mapping[str, Any],
    config: RunnableConfig | None,
) -> dict[str, Any]:
    source_obj = state.get("source")
    source: Optional[Source] = source_obj if isinstance(source_obj, Source) else None
    content = state.get("input_text")
    assert source is not None or content, "No content to transform"
    transformation = cast(Transformation, state["transformation"])
    if not content:
        assert source is not None
        content = source.full_text
    transformation_template_text = transformation.prompt
    default_prompts: DefaultPrompts = DefaultPrompts(transformation_instructions=None)
    if default_prompts.transformation_instructions:
        transformation_template_text = f"{default_prompts.transformation_instructions}\n\n{transformation_template_text}"

    transformation_template_text = f"{transformation_template_text}\n\n# INPUT"

    system_prompt = Prompter(template_text=transformation_template_text).render(
        data=dict(state)
    )
    content_str = str(content) if content else ""

    prompt_tokens = token_count(f"{system_prompt}\n{content_str}")
    if prompt_tokens > MAX_PROMPT_TOKENS:
        logger.info(f"Content too large ({prompt_tokens} tokens), using chunked processing")
        cleaned_content = await _process_chunked_transformation(
            system_prompt, content_str, config
        )
    else:
        cleaned_content = await _process_single_transformation(
            system_prompt, content_str, config
        )

    if source is not None:
        await source.add_insight(transformation.title, cleaned_content)

    return {
        "output": cleaned_content,
    }


async def _process_single_transformation(
    system_prompt: str, content: str, config: RunnableConfig | None
) -> str:
    payload = [SystemMessage(content=system_prompt), HumanMessage(content=content)]
    config_mapping = cast(Mapping[str, Any], config or {})
    configurable = cast(Mapping[str, Any], config_mapping.get("configurable", {}))
    model_id = configurable.get("model_id")

    chain = await provision_langchain_model(
        f"{system_prompt}\n{content}",
        model_id,
        "transformation",
        max_tokens=5055,
    )

    response = await chain.ainvoke(payload)
    response_content = (
        response.content if isinstance(response.content, str) else str(response.content)
    )
    return clean_thinking_content(response_content)


async def _process_chunked_transformation(
    system_prompt: str, content: str, config: RunnableConfig | None
) -> str:
    from open_notebook.utils import split_text

    system_tokens = token_count(system_prompt)
    chunk_token_limit = MAX_PROMPT_TOKENS - system_tokens - 1000
    
    chunks = split_text(content, max_tokens=chunk_token_limit)
    logger.info(f"Split content into {len(chunks)} chunks for processing")
    
    chunk_results = []
    config_mapping = cast(Mapping[str, Any], config or {})
    configurable = cast(Mapping[str, Any], config_mapping.get("configurable", {}))
    model_id = configurable.get("model_id")
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i+1}/{len(chunks)}")
        payload = [SystemMessage(content=system_prompt), HumanMessage(content=chunk)]
        
        chain = await provision_langchain_model(
            f"{system_prompt}\n{chunk}",
            model_id,
            "transformation",
            max_tokens=5055,
        )
        
        response = await chain.ainvoke(payload)
        response_content = (
            response.content if isinstance(response.content, str) else str(response.content)
        )
        chunk_results.append(clean_thinking_content(response_content))
    
    if len(chunk_results) == 1:
        return chunk_results[0]
    
    merge_prompt = (
        "Merge the following insights from different sections of a document into a single, "
        "coherent summary. Remove redundancies and organize the information logically:\n\n"
    )
    combined = "\n\n---\n\n".join(f"Section {i+1}:\n{r}" for i, r in enumerate(chunk_results))
    
    merge_payload = [SystemMessage(content=merge_prompt), HumanMessage(content=combined)]
    merge_chain = await provision_langchain_model(
        f"{merge_prompt}\n{combined}",
        model_id,
        "transformation",
        max_tokens=5055,
    )
    
    merge_response = await merge_chain.ainvoke(merge_payload)
    merge_content = (
        merge_response.content if isinstance(merge_response.content, str) else str(merge_response.content)
    )
    return clean_thinking_content(merge_content)


agent_state = StateGraph(TransformationState)
agent_state.add_node("agent", run_transformation)  # type: ignore[type-var]
agent_state.add_edge(START, "agent")
agent_state.add_edge("agent", END)
graph = agent_state.compile()
