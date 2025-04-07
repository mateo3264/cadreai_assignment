# Configuration and imports
import os
import json
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import logging
import re
from llm_calls import BaseClient, OpenAIClient
from templates import CLASSIFICATION_TEMPLATE, RESPONSES_TEMPLATE
from sample_emails import sample_emails
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()



class EmailProcessor:
    def __init__(self, client: BaseClient):
        """Initialize the email processor with OpenAI API key."""
        self.client = client

        # Define valid categories
        self.valid_categories = {
            "complaint", "inquiry", "feedback",
            "support_request", "other"
        }

        self.required_fields = {
            "id",
            "from",
            "subject",
            "body",
            "timestamp"
        }

    @staticmethod
    def load_data(data_source: Any) -> list:
        if isinstance(data_source, list):
            return data_source
        
        if isinstance(data_source, str) and os.path.exists(data_source):
            if data_source.endswith('.json'):
                df = pd.read_json(data_source)
                raw_emails = df.to_dict(orient='records')
            
            elif data_source.endswith('.csv'):
                df = pd.read_json(data_source)
                raw_emails = df.to_dict(orient='records')
            
            else:
                raise ValueError(f'Invalid file format {data_source}')
        
        elif hasattr(data_source, 'to_dict') and callable(data_source.to_dict):
            raw_emails = df.to_dict(orient='records')
        
        else:
            raise ValueError(f'Invalid data type for: {data_source}')
        
        return raw_emails

    def validate_email_format(self, email: Dict[str, str]) -> bool:
        # Validate fields of email
        for field in self.required_fields:
            if field not in email or email[field] is None:
                logger.warning(f"Required field missing: {field}")
                return False
            
        # Validate ID format
        if not re.match(r'^\d{3}$', email['id']):
            logger.warning(f"Invalid ID format {email['id']} - 3 digits required")
            return False    

        # Validate body is not empty
        if not email['body'].split():
            logger.warning(f"Body must not be empty {email['id']}")
            return False
        
        # Validate timestamp format
        try:
            datetime.fromisoformat(email['timestamp'].replace('Z', '+00:00'))
        except Exception as e:
            logger.warning(f"Invalid timestamp format {email['timestamp']}")
            return False
        
        return True

    def get_email_subject_and_body(self, email: Dict[str, str]) -> str:
        subject = email['subject']
        body = email['body']

        result = "Subject:\n" + subject + '\n\n' + "Body:\n" + body
        print('result: ', result)
        return result



    def classify_email(self, email: Dict[str, str]) -> Optional[str]:
        """
        Classify an email using LLM.
        Returns the classification category or None if classification fails.
        
        TODO: 
        1. Design and implement the classification prompt
        2. Make the API call with appropriate error handling
        3. Validate and return the classification
        """
        
        
        classification_prompt = CLASSIFICATION_TEMPLATE.format(
            categories=', '.join(self.valid_categories),
            email_data=self.get_email_subject_and_body(email)
        )
        classification = self.client.get_classification(email, classification_prompt)
        
        if classification in self.valid_categories:
            return classification
        else:
            logger.warning(f"Error while classifying email with ID: {email['id']}")
            return None

    def generate_response(self, email: Dict, classification: str) -> Optional[str]:
        """
        Generate an automated response based on email classification.
        
        TODO:
        1. Design the response generation prompt
        2. Implement appropriate response templates
        3. Add error handling
        """
        
        response_prompts = {
            # Compliant
            "complaint": "Apologize sincerely, offer a resolution, and ask for any additional details.",
            # Inquiry
            "inquiry": "Provide a clear, helpful answer. Offer further assistance if needed.",
            # Feedback
            "feedback": "Thank the customer and explain how their feedback is valued.",
            # Support_request
            "support_request": "Acknowledge the issue and inform that a support ticket has been created.",
            # Other
            "other": "Respond politely and offer to assist further if needed.",
            # Spam
            "spam": "Respond only with: [NO_RESPONSE]"
            
        }

        response_prompt = RESPONSES_TEMPLATE.format(
            classification=classification,
            specific_classification_instruction=response_prompts[classification],
            email_data=self.get_email_subject_and_body(email)
        )
        response = self.client.get_response(email, response_prompt)

        return response

class EmailAutomationSystem:
    def __init__(self, processor: EmailProcessor):
        """Initialize the automation system with an EmailProcessor."""
        self.processor = processor
        self.response_handlers = {
            "complaint": self._handle_complaint,
            "inquiry": self._handle_inquiry,
            "feedback": self._handle_feedback,
            "support_request": self._handle_support_request,
            "other": self._handle_other
        }

    def process_email(self, email: Dict) -> Dict:
        """
        Process a single email through the complete pipeline.
        Returns a dictionary with the processing results.
        
        TODO:
        1. Implement the complete processing pipeline
        2. Add appropriate error handling
        3. Return processing results
        """
        result = {
            "email_id":email['id'],
            "success":False,
            "classification":None,
            "response_sent":False
        }

        try:
            if not self.processor.validate_email_format(email):
                logger.warning(f"Invalid email format for email with ID: {email['id']}")
                return result
            classification = self.processor.classify_email(email) or "other"
            
            result["classification"] = classification
            

            response = self.processor.generate_response(email, classification)

            if not response:
                raise ValueError(f"Error while generating response for email with ID: {email['id']}")
            
            self.response_handlers.get(classification, self._handle_other)(email, response)
            result.update({"success": True, "response_sent": True})
        except Exception as e:
            logger.error(f"Error while processing email with ID: {email['id']}")
            create_support_ticket(email['id'], f'Error: {e}')
        
        return result

    def _handle_complaint(self, email: Dict, response: str):
        """
        Handle complaint emails.
        TODO: Implement complaint handling logic
        """
        create_urgent_ticket(email['id'], 'complaint', self.processor.get_email_subject_and_body(email))
        send_complaint_response(email['id'], response)

    def _handle_inquiry(self, email: Dict, response: str):
        """
        Handle inquiry emails.
        TODO: Implement inquiry handling logic
        """
        send_standard_response(email['id'], response)

    def _handle_feedback(self, email: Dict, response: str):
        """
        Handle feedback emails.
        TODO: Implement feedback handling logic
        """
        log_customer_feedback(email['id'], self.processor.get_email_subject_and_body(email))
        send_standard_response(email['id'], response)

    def _handle_support_request(self, email: Dict, response: str):
        """
        Handle support request emails.
        TODO: Implement support request handling logic
        """
        create_support_ticket(email['id'], self.processor.get_email_subject_and_body(email))
        send_standard_response(email['id'], response)

    def _handle_other(self, email: Dict, response: str):
        """
        Handle other category emails.
        TODO: Implement handling logic for other categories
        """
        create_support_ticket(email['id'], self.processor.get_email_subject_and_body(email))
        send_standard_response(email['id'], response)

# Mock service functions
def send_complaint_response(email_id: str, response: str):
    """Mock function to simulate sending a response to a complaint"""
    logger.info(f"Sending complaint response for email {email_id}")
    # In real implementation: integrate with email service


def send_standard_response(email_id: str, response: str):
    """Mock function to simulate sending a standard response"""
    logger.info(f"Sending standard response for email {email_id}")
    # In real implementation: integrate with email service


def create_urgent_ticket(email_id: str, category: str, context: str):
    """Mock function to simulate creating an urgent ticket"""
    logger.info(f"Creating urgent ticket for email {email_id}")
    # In real implementation: integrate with ticket system


def create_support_ticket(email_id: str, context: str):
    """Mock function to simulate creating a support ticket"""
    logger.info(f"Creating support ticket for email {email_id}")
    # In real implementation: integrate with ticket system


def log_customer_feedback(email_id: str, feedback: str):
    """Mock function to simulate logging customer feedback"""
    logger.info(f"Logging feedback for email {email_id}")
    # In real implementation: integrate with feedback system


def run_demonstration():
    """Run a demonstration of the complete system."""
    # Initialize the system
    openai_client = OpenAIClient()
    processor = EmailProcessor(openai_client)
    automation_system = EmailAutomationSystem(processor)

    email_to_process = processor.load_data(sample_emails)
    
    # Process all sample emails
    results = []
    for email in email_to_process:
        logger.info(f"\nProcessing email {email['id']}...")
        result = automation_system.process_email(email)
        results.append(result)

    # Create a summary DataFrame
    df = pd.DataFrame(results)
    print("\nProcessing Summary:")
    print(df[["email_id", "success", "classification", "response_sent"]])

    return df


# Example usage:
if __name__ == "__main__":
    results_df = run_demonstration()