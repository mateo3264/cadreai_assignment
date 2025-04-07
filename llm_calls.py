from openai import OpenAI
from typing import Dict, Optional
import logging
from abc import ABC, abstractmethod
from templates import SYSTEM_PROMPT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseClient(ABC):
    @abstractmethod
    def get_classification(self, email: Dict[str, str], classification_prompt: str) -> Optional[str]:
        pass
    
    @abstractmethod
    def get_response(self, email: Dict[str, str], response_prompt: str, temperature: float = 0.5) -> Optional[str]:
        pass


class OpenAIClient(BaseClient):
    def __init__(self, model: str = 'gpt-4o-mini'):
        self.model = model
        self.client = OpenAI()
    
    def get_classification(self, email: Dict[str, str], classification_prompt: str) -> Optional[str]:
        try:
            completions = self.client.chat.completions.create(
                model=self.model,
                temperature=0.0,
                messages=[
                    {
                        "role":"system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": classification_prompt
                    }
                ]
            )

            classification = completions.choices[0].message.content
            classification = classification.lower().strip().rstrip('.')

            return classification
        except Exception as e:
            logger.warning(f"Error while classifying ID: {email['id']}")
            return None
    
    def get_response(self, email: Dict[str, str], response_prompt: str, temperature: float = 0.5) -> Optional[str]:
        try:
            completions = self.client.chat.completions.create(
                model=self.model,
                temperature=temperature,
                messages=[
                    {
                        "role":"system",
                        "content": SYSTEM_PROMPT
                    },
                    {
                        "role": "user",
                        "content": response_prompt
                    }
                ]
            )

            response = completions.choices[0].message.content
            

            return response
        except Exception as e:
            logger.warning(f"Error while generating response ID: {email['id']}")
            return None