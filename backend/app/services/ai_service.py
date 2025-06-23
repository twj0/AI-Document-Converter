# backend/app/services/ai_service.py

import logging
import json
from abc import ABC, abstractmethod
from typing import Dict, Any

# Placeholder for configuration. In our final app, this will import a Pydantic
# settings object that loads API keys from a .env file.
# from ..core.config import settings

# For now, we'll simulate it for standalone testing.
import os

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Custom Exception Class ---
class AIServiceError(Exception):
    """Custom exception for AI service failures."""
    pass

# --- Library Availability Checks ---
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("`google-generativeai` library not found. Gemini provider will be unavailable.")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("`openai` library not found. OpenAI provider will be unavailable.")

# --- Abstract Base Class for LLM Providers ---

class LLMProvider(ABC):
    """An abstract base class for all Large Language Model providers."""

    def __init__(self, model_name: str, api_key: str):
        if not api_key:
            raise ValueError("API key must be provided.")
        self.model_name = model_name
        self.api_key = api_key
        self._initialize_client()
        logger.info(f"{self.__class__.__name__} initialized for model '{self.model_name}'.")

    @abstractmethod
    def _initialize_client(self):
        """Initializes the specific SDK client for the provider."""
        pass

    @abstractmethod
    def generate_structured_markdown(self, text_content: str, subject: str, file_type: str) -> Dict[str, Any]:
        """

        Generates structured content from the AI.

        Args:
            text_content: The raw text extracted from the document.
            subject: The subject of the document (e.g., "Thermodynamics").
            file_type: The original file type hint (e.g., "PDF", "DOCX").

        Returns:
            A dictionary with a defined structure, e.g.:
            {
                "markdown_content": "...",
                "warnings": ["Table on page 3 was too complex..."]
            }
        """
        pass

    def _get_prompt_template(self) -> str:
        """
        Returns the advanced prompt template asking for a structured JSON output.
        This is the core of our "best-effect" strategy.
        """
        return """
        You are an expert-level document processing AI. Your task is to convert raw, potentially messy text extracted from a file into a clean, well-structured Markdown document. You must also identify and report any issues you encounter during the conversion.

        **CRITICAL INSTRUCTION: Your final output must be a single, valid JSON object. Do not output any text before or after the JSON object.**

        The JSON object must have the following structure:
        {
          "markdown_content": "...",
          "warnings": []
        }

        **Field Explanations:**
        1.  `markdown_content` (string): This field must contain the fully converted, high-quality Markdown text.
        2.  `warnings` (array of strings): This field is for reporting problems. If you encounter any issues like complex tables you cannot convert, unrecoverable garbled text, or missing figures you have to describe, you MUST add a descriptive string for each issue into this array. If there are no issues, return an empty array `[]`.

        **Conversion Rules for `markdown_content`:**
        - **Headings:** Use `#`, `##`, `###` for titles and subtitles.
        - **Lists:** Convert numbered and bulleted lists to proper Markdown lists.
        - **Formatting:** Use `**bold**` and `*italics*` where appropriate.
        - **Formulas:** All mathematical formulas MUST be in LaTeX format. Inline formulas use `$E=mc^2$`, and block formulas use `$$...$$`.
        - **Code Blocks:** Use triple backticks (```) for code, specifying the language if possible.
        - **Tables:** Recreate simple tables using Markdown table syntax. For very complex tables, do not attempt to create them; instead, add a warning to the `warnings` array explaining the issue and describe the table's content in the text.
        - **Placeholders:** For fill-in-the-blanks, use `____`. For judgment questions, use `( )`.
        - **Readability:** Ensure proper spacing and newlines between paragraphs, questions, and sections.

        **Self-Correction:** Before finalizing your JSON output, review the `markdown_content`. Ensure all LaTeX is valid, lists are formatted correctly, and the structure is logical.

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


# --- Concrete Implementations ---

class GeminiProvider(LLMProvider):
    """LLM Provider for Google's Gemini models."""

    def _initialize_client(self):
        if not GEMINI_AVAILABLE:
            raise RuntimeError("Gemini SDK not installed. Please run 'pip install google-generativeai'.")
        genai.configure(api_key=self.api_key)
        self.client = genai.GenerativeModel(self.model_name)

    def generate_structured_markdown(self, text_content: str, subject: str, file_type: str) -> Dict[str, Any]:
        prompt = self._get_prompt_template().format(
            subject=subject, file_type=file_type, text_content=text_content
        )
        logger.info(f"Sending request to Gemini model '{self.model_name}'...")
        try:
            # Enforce JSON output format
            generation_config = genai.types.GenerationConfig(
                response_mime_type="application/json"
            )
            response = self.client.generate_content(prompt, generation_config=generation_config)

            if not response.candidates:
                feedback = response.prompt_feedback
                raise AIServiceError(f"Gemini API returned no candidates. Feedback: {feedback}")
            
            # The response.text should be a valid JSON string
            response_text = response.text
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Gemini: {e}\nResponse text: {response.text[:500]}...")
            raise AIServiceError("AI returned an invalid JSON object.")
        except Exception as e:
            logger.error(f"An error occurred with the Gemini API: {e}")
            raise AIServiceError(str(e))


class OpenAIProvider(LLMProvider):
    """LLM Provider for OpenAI's models (e.g., GPT-4o)."""

    def _initialize_client(self):
        if not OPENAI_AVAILABLE:
            raise RuntimeError("OpenAI SDK not installed. Please run 'pip install openai'.")
        self.client = openai.OpenAI(api_key=self.api_key)

    def generate_structured_markdown(self, text_content: str, subject: str, file_type: str) -> Dict[str, Any]:
        prompt = self._get_prompt_template().format(
            subject=subject, file_type=file_type, text_content=text_content
        )
        logger.info(f"Sending request to OpenAI model '{self.model_name}'...")
        try:
            # Enforce JSON output format with GPT-4 Turbo and newer models
            response = self.client.chat.completions.create(
                model=self.model_name,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are a helpful document processing assistant designed to output JSON."},
                    {"role": "user", "content": prompt}
                ]
            )
            response_text = response.choices.message.content
            return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from OpenAI: {e}\nResponse text: {response.choices.message.content[:500]}...")
            raise AIServiceError("AI returned an invalid JSON object.")
        except Exception as e:
            logger.error(f"An error occurred with the OpenAI API: {e}")
            raise AIServiceError(str(e))


# --- Factory Function ---

def get_ai_provider(
    provider_name: str, 
    model_name: str, 
    api_key: str
) -> LLMProvider:
    """
    Factory function to get an instance of the specified AI provider.

    Args:
        provider_name: The name of the provider (e.g., "gemini", "openai").
        model_name: The specific model name to use.
        api_key: The API key for the service.

    Returns:
        An instance of a class that inherits from LLMProvider.

    Raises:
        ValueError: If the provider name is not supported.
    """
    provider_name = provider_name.lower()
    if provider_name == "gemini":
        return GeminiProvider(model_name=model_name, api_key=api_key)
    elif provider_name == "openai":
        return OpenAIProvider(model_name=model_name, api_key=api_key)
    # Add other providers like "zhipuai" here in the future
    # elif provider_name == "zhipuai":
    #     return ZhipuAIProvider(...)
    else:
        raise ValueError(f"Unsupported AI provider: '{provider_name}'")

# --- Example Usage (for standalone testing) ---
if __name__ == '__main__':
    # This block will only run when you execute this file directly.
    # It demonstrates how to use the service.
    # Make sure you have set the API key in your environment variables.
    
    logger.info("Running AI service standalone test...")
    
    # --- Test Gemini ---
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    if gemini_api_key and GEMINI_AVAILABLE:
        try:
            print("-" * 20)
            logger.info("Testing Gemini Provider...")
            gemini_provider = get_ai_provider(
                provider_name="gemini",
                model_name="gemini-1.5-flash-latest",
                api_key=gemini_api_key
            )
            sample_text = "1. What is 2+2?\n2. A complex table here."
            result = gemini_provider.generate_structured_markdown(
                text_content=sample_text,
                subject="Simple Math",
                file_type="TXT"
            )
            print("Gemini Result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("-" * 20)
        except (RuntimeError, ValueError, AIServiceError) as e:
            logger.error(f"Gemini test failed: {e}")
    else:
        logger.warning("Skipping Gemini test: API key not set or SDK not installed.")

    # --- Test OpenAI ---
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key and OPENAI_AVAILABLE:
        try:
            print("-" * 20)
            logger.info("Testing OpenAI Provider...")
            openai_provider = get_ai_provider(
                provider_name="openai",
                model_name="gpt-4o", # Or "gpt-3.5-turbo-1106" or newer for JSON mode
                api_key=openai_api_key
            )
            sample_text = "1. What is the capital of France?\n- Paris\n- London"
            result = openai_provider.generate_structured_markdown(
                text_content=sample_text,
                subject="Geography",
                file_type="DOCX"
            )
            print("OpenAI Result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print("-" * 20)
        except (RuntimeError, ValueError, AIServiceError) as e:
            logger.error(f"OpenAI test failed: {e}")
    else:
        logger.warning("Skipping OpenAI test: API key not set or SDK not installed.")