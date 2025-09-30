import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import yaml
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    """Configuration for Sakana Desktop Assistant"""
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    data_dir: Path = None
    models_dir: Path = None
    plugins_dir: Path = None
    
    # LLM Settings
    llm_provider: str = "local"  # local, openai, anthropropic, gemini/google, grok
    model_name: str = "llama-3.2-3b"
    api_key: Optional[str] = None
    # Optional base URL for OpenAI-compatible endpoints (e.g., Ollama, LocalAI)
    openai_base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048

    # Provider-specific credentials (optional; loaded from env if not set)
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None  # Google Generative AI (Gemini)
    xai_api_key: Optional[str] = None     # xAI (Grok)
    xai_base_url: Optional[str] = None    # Custom base URL for xAI if needed
    
    # Memory Settings
    memory_db_path: Path = None
    max_short_term_memory: int = 100
    max_long_term_memory: int = 10000
    
    # Learning Settings
    learning_rate: float = 0.01
    evolution_generations: int = 10
    population_size: int = 20
    mutation_rate: float = 0.1
    
    # Security Settings
    sandbox_enabled: bool = True
    max_execution_time: int = 30  # seconds
    allowed_operations: list = None
    audit_log_path: Path = None
    
    # UI Settings
    enable_gui: bool = True
    # --- NEW: React UI migration flags ---
    # Clear comments for easy debug; when enabled, the HTTP server will serve the React build from react_ui_dist_dir.
    react_ui_enabled: bool = False
    # Default dist directory where `npm run build` outputs the SPA assets
    react_ui_dist_dir: Path = Path(__file__).parent.parent.parent / "src" / "ui" / "webapp" / "dist"

    # Duplicate from_yaml/to_yaml removed; see single canonical implementations above.
    pass
    enable_voice: bool = False
    theme: str = "dark"

    # Tool Selection (adaptive) Settings
    tool_selection_enabled: bool = True
    tool_selection_exploration_rate: float = 0.1  # epsilon for epsilon-greedy
    tool_selection_min_samples: int = 5  # min calls before exploitation kicks in
    
    def __post_init__(self):
        # Set default paths
        if self.data_dir is None:
            self.data_dir = self.base_dir / "data"
        if self.models_dir is None:
            self.models_dir = self.base_dir / "models"
        if self.plugins_dir is None:
            self.plugins_dir = self.base_dir / "plugins"
        if self.memory_db_path is None:
            self.memory_db_path = self.data_dir / "memory.db"
        if self.audit_log_path is None:
            self.audit_log_path = self.data_dir / "audit.log"
        
        # Create directories
        self.data_dir.mkdir(exist_ok=True)
        self.models_dir.mkdir(exist_ok=True)
        self.plugins_dir.mkdir(exist_ok=True)
        
        # Set default allowed operations
        if self.allowed_operations is None:
            self.allowed_operations = [
                "read_file",
                "write_file",
                "execute_code",
                "search_web",
                "manage_tasks"
            ]
        
        # Load generic API key from environment (backward-compatible)
        if self.api_key is None:
            self.api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        
        # Load OpenAI-compatible base URL from environment (e.g., Ollama/LocalAI)
        if self.openai_base_url is None:
            self.openai_base_url = os.getenv("OPENAI_BASE_URL")

        # Provider-specific env fallbacks (do not override explicit config fields)
        if self.anthropic_api_key is None:
            self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if self.gemini_api_key is None:
            # Google uses GOOGLE_API_KEY. Also accept GEMINI_API_KEY for user convenience
            self.gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if self.xai_api_key is None:
            # xAI (Grok) uses XAI_API_KEY; also accept GROK_API_KEY
            self.xai_api_key = os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY")
        if self.xai_base_url is None:
            self.xai_base_url = os.getenv("XAI_BASE_URL") or os.getenv("GROK_BASE_URL")
    
    @classmethod
    def from_yaml(cls, path: Path) -> "Config":
        """Load configuration from YAML file
        Note: Coerce known path-like fields to Path for consistency.
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Convert path-like fields to Path objects
        path_fields = ['models_dir', 'plugins_dir', 'logs_dir', 'sessions_dir', 'tmp_dir', 'memory_db_path', 'react_ui_dist_dir']
        for field in path_fields:
            if field in data and data[field] is not None:
                data[field] = Path(data[field])
        
        return cls(**data)
    
    def to_yaml(self, path: Path):
        """Save configuration to YAML file"""
        data = {
            k: str(v) if isinstance(v, Path) else v
            for k, v in self.__dict__.items()
        }
        with open(path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)