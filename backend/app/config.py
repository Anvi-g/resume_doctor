"""
Configuration settings for Resume Doctor (Azure AI-103).

Loads environment variables from local `.env` file for Azure OpenAI Service configuration.
"""

import os               # Environment variable loading
from dotenv import load_dotenv  # Dotenv library to read key-value pairs from .env file

# Load environment variables into process environment
load_dotenv()

# Azure OpenAI Endpoint URL (e.g., https://my-openai-resource.openai.azure.com/)
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "")

# Azure OpenAI Resource API Key
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "")

# Azure OpenAI Deployment Name (Default: gpt-4o)
AZURE_OPENAI_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

# Azure OpenAI API Version (Default: 2024-02-15-preview)
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
