"""Configuration management for Chronos agent."""

import os
from typing import Optional, Any
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class ModelConfig:
    """LLM Model configuration."""
    
    name: str = "meta-llama/Meta-Llama-3-8B-Instruct"
    quantization: str = "4bit"
    max_new_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    device_map: str = "auto"
    load_in_4bit: bool = True
    bnb_4bit_compute_dtype: str = "float16"
    bnb_4bit_quant_type: str = "nf4"


@dataclass
class AgentConfig:
    """Agent behavior configuration."""
    
    max_iterations: int = 10
    timeout: int = 300  # seconds
    enable_memory: bool = True
    memory_window: int = 10
    verbose: bool = True
    stream_response: bool = True


@dataclass
class GoogleConfig:
    """Google API configuration."""
    
    client_id: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_ID"))
    client_secret: Optional[str] = field(default_factory=lambda: os.getenv("GOOGLE_CLIENT_SECRET"))
    redirect_uri: str = "http://localhost:8000/oauth/callback"
    scopes: list[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/calendar.events",
    ])
    credentials_file: Path = Path("credentials.json")
    token_file: Path = Path("token.json")


@dataclass
class DPOConfig:
    """DPO training configuration."""
    
    learning_rate: float = 5e-7
    batch_size: int = 4
    epochs: int = 3
    beta: float = 0.1
    max_length: int = 512
    max_prompt_length: int = 256
    gradient_accumulation_steps: int = 4
    warmup_steps: int = 100
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 50


@dataclass
class APIConfig:
    """API server configuration."""
    
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    reload: bool = True
    log_level: str = "info"
    cors_origins: list[str] = field(default_factory=lambda: ["*"])


@dataclass
class DatabaseConfig:
    """Database configuration."""
    
    url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./chronos.db"))
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


@dataclass
class Config:
    """Main application configuration."""
    
    # Environment
    env: str = field(default_factory=lambda: os.getenv("ENV", "development"))
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "true").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # API Keys
    hf_token: Optional[str] = field(default_factory=lambda: os.getenv("HUGGINGFACE_TOKEN"))
    openai_api_key: Optional[str] = field(default_factory=lambda: os.getenv("OPENAI_API_KEY"))
    
    # Sub-configurations
    model: ModelConfig = field(default_factory=ModelConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    dpo: DPOConfig = field(default_factory=DPOConfig)
    api: APIConfig = field(default_factory=APIConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    
    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = field(default_factory=lambda: Path("data"))
    models_dir: Path = field(default_factory=lambda: Path("models"))
    logs_dir: Path = field(default_factory=lambda: Path("data/logs"))
    
    def __post_init__(self):
        """Create necessary directories."""
        for dir_path in [self.data_dir, self.models_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls()
    
    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "env": self.env,
            "debug": self.debug,
            "log_level": self.log_level,
            "model": self.model.__dict__,
            "agent": self.agent.__dict__,
            "api": self.api.__dict__,
        }


# Global configuration instance
config = Config.from_env()

