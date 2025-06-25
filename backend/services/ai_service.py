# backend/services/ai_service.py
import logging
import json
from abc import ABC, abstractmethod

# 库可用性检查
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AIServiceError(Exception):
    pass

class LLMProvider(ABC):
    def __init__(self, model_name: str, api_key: str):
        if not api_key: raise ValueError("API key must be provided.")
        self.model_name, self.api_key = model_name, api_key
        self._initialize_client()

    @abstractmethod
    def _initialize_client(self):
        pass

    def _get_prompt_template(self) -> str:
        # 这个强大的 JSON 结构化 Prompt 保持不变
        return """
        You are an expert document processing AI. Your task is to convert raw, potentially messy text from a file into a clean, well-structured Markdown document.

        **CRITICAL INSTRUCTION: Your final output must be a single, valid JSON object with the following structure:**
        {
          "markdown_content": "...",
          "warnings": []
        }

        **Field Explanations:**
        1.  `markdown_content` (string): The fully converted, high-quality Markdown text.
        2.  `warnings` (array of strings): Report any issues encountered during conversion (e.g., complex tables, unrecoverable garbled text). If no issues, return an empty array `[]`.

        **Conversion Rules:**
        - **Headings & Formatting:** Use `#`, `##`, `**bold**`, etc.
        - **Formulas:** All mathematical formulas MUST be in LaTeX format (`$inline$`, `$$block$$`).
        - **Tables:** Recreate simple tables. For complex tables, add a warning and describe the table in the text.

        ---
        **Document Context:**
        - Subject: "{subject}"
        - Original File Type: "{file_type}"

        **Raw Text Content to Process:**
        ---
        {text_content}
        ---
        Now, process the text and provide your response in the specified JSON format.
        """
    
    @abstractmethod
    def generate_structured_markdown(self, text_content: str, subject: str, file_type: str) -> dict:
        pass

class GeminiProvider(LLMProvider):
    def _initialize_client(self):
        if not GEMINI_AVAILABLE: raise RuntimeError("Gemini SDK not installed.")
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model_name)

    def generate_structured_markdown(self, text_content: str, subject: str, file_type: str) -> dict:
        prompt = self._get_prompt_template().format(subject=subject, file_type=file_type, text_content=text_content)
        try:
            response = self.client.generate_content(prompt, generation_config=genai.types.GenerationConfig(response_mime_type="application/json"))
            return json.loads(response.text)
        except Exception as e:
            raise AIServiceError(f"Gemini API Error: {e}")

class OpenAIProvider(LLMProvider):
    def _initialize_client(self):
        if not OPENAI_AVAILABLE: raise RuntimeError("OpenAI SDK not installed.")
        self.client = OpenAI(api_key=self.api_key)
    
    def generate_structured_markdown(self, text_content: str, subject: str, file_type: str) -> dict:
        prompt = self._get_prompt_template().format(subject=subject, file_type=file_type, text_content=text_content)
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}]
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            raise AIServiceError(f"OpenAI API Error: {e}")


def get_ai_provider(provider_name: str, model_name: str, api_key: str) -> LLMProvider:
    provider_map = {
        "gemini": GeminiProvider,
        "openai": OpenAIProvider
    }
    provider_class = provider_map.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unsupported AI provider: '{provider_name}'")
    return provider_class(model_name=model_name, api_key=api_key)