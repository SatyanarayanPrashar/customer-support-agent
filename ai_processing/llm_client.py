from typing import Dict,  Any
import openai

from utils.logger import get_logger
logger = get_logger()

class LLM_Client:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AIWorker with configuration.
        """
        self.model_name: str = config['ai_processing']['model']
        self.api_key: str = config['api_keys']['openai_api']
        self.temperature: float = config['ai_processing'].get('temperature', 0.7)
        self.client = self._init_client()

    def _init_client(self):
        """
        Initializes the GenAI client.
        """
        return openai.OpenAI(
            api_key=self.api_key
        )

    def invoke(self, conversation: list):
        """
        Generate response from the AI.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=conversation
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            return ""
