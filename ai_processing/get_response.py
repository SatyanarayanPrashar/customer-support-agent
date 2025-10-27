import json
from google import genai
import time
from typing import Dict,  Any

import openai
import yaml

from utils.logger import get_logger
logger = get_logger()

class Get_repsonse:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AIWorker with configuration.
        """
        self.model_name: str = config['ai_processing']['model']
        self.api_key: str = config['api_keys']['openai_api']
        self.temperature: float = config['ai_processing'].get('temperature', 0.7)

        # Initialize the client
        self.client = self._init_client()

        # Load system prompt from file
        self.system_prompt: str = self._load_system_prompt()

        self.max_retries = 3
        self.retry_delay = 2 # seconds

    def _init_client(self) -> genai.Client:
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
