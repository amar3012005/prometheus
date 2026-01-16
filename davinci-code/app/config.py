import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Keys
    gemini_api_key: str = "AIzaSyBG9nb_Xe2267oBO9s0g0jJOQtJGh47pNk"
    elevenlabs_api_key: Optional[str] = "sk_fa0ad2176bbcc1b6b31a99b233bc77ba834178ad2980ec90"
    groq_api_key: str = os.getenv("GROQ_API_KEY", "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")
    
    # LLM Settings
    llm_model: str = "llama-3.1-8b-instant"
    llm_temperature: float = 0.7
    
    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8099
    
    # Deployment Settings
    deployment_mode: str = "k3s"  # "mock" or "k3s"
    
    # Paths (Default to relative paths for host/docker compatibility)
    vault_base_path: str = "vault"
    helm_chart_path: str = "davinci-agent-chart"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

settings = Settings()
