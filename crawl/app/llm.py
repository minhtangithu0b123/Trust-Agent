"""Provider-neutral structured generation for the legal agents."""

from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel


class ModelConfigurationError(RuntimeError):
    pass


class GeminiStructuredModel:
    def __init__(self, *, api_key: str, model: str, schema: Type[BaseModel]):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise ModelConfigurationError(
                "Gemini provider requires google-genai; install the project dependencies"
            ) from exc
        self._client = genai.Client(api_key=api_key)
        self._types = types
        self._model = model
        self._schema = schema

    def invoke(self, prompt: str) -> BaseModel:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=self._schema,
                temperature=0,
            ),
        )
        parsed: Any = getattr(response, "parsed", None)
        if isinstance(parsed, self._schema):
            return parsed
        if parsed is not None:
            return self._schema.model_validate(parsed)
        text = getattr(response, "text", None)
        if not text:
            raise ValueError("Gemini returned no structured response")
        return self._schema.model_validate_json(text)


def build_structured_model(settings: Any, schema: Type[BaseModel]):
    provider = str(getattr(settings, "llm_provider", "openai")).strip().casefold()
    if provider == "gemini":
        api_key = getattr(settings, "gemini_api_key", None)
        if not api_key:
            raise ModelConfigurationError("GEMINI_API_KEY is not configured")
        return GeminiStructuredModel(
            api_key=api_key,
            model=getattr(settings, "gemini_model", "gemini-3.5-flash-lite"),
            schema=schema,
        )
    if provider == "openai":
        api_key = getattr(settings, "openai_api_key", None)
        if not api_key:
            raise ModelConfigurationError("OPENAI_API_KEY is not configured")
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ModelConfigurationError("OpenAI provider requires langchain-openai") from exc
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=api_key,
            temperature=0,
        ).with_structured_output(schema)
    raise ModelConfigurationError(f"Unsupported LLM_PROVIDER: {provider}")
