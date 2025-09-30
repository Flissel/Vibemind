#!/usr/bin/env python3
"""
Sakana Desktop Assistant - Self-learning AI assistant inspired by Sakana AI
"""

import asyncio
import signal
import sys
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
import argparse
from typing import Optional
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import Config, SakanaAssistant
from src.ui.cli_interface import CLIInterface

# Configure DATA_DIR
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = Path(os.getenv('DATA_DIR', PROJECT_ROOT / 'data'))
LOGS_DIR = DATA_DIR / 'logs'
SESSIONS_DIR = DATA_DIR / 'sessions'
TMP_DIR = DATA_DIR / 'tmp'

# Ensure directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
TMP_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging with rotating file handlers
def setup_logging():
    """Setup logging with rotating file handlers under data/logs/"""
    
    # Create rotating file handler
    file_handler = RotatingFileHandler(
        LOGS_DIR / 'assistant.log',
        maxBytes=20 * 1024 * 1024,  # 20MB
        backupCount=10,
        encoding='utf-8'
    )
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

# Setup logging
setup_logging()

logger = logging.getLogger(__name__)

class AssistantRunner:
    """Main runner for the assistant"""
    
    def __init__(self, config_path: Optional[Path] = None):
        # Load configuration
        if config_path and config_path.exists():
            self.config = Config.from_yaml(config_path)
        else:
            self.config = Config()
        
        # Set data directory paths for use by other components
        self.config.data_dir = DATA_DIR
        self.config.logs_dir = LOGS_DIR
        self.config.sessions_dir = SESSIONS_DIR
        self.config.tmp_dir = TMP_DIR
        
        self.assistant = None
        self.interface = None
        self.running = False
    
    async def initialize(self):
        """Initialize the assistant and selected interface"""
        self.assistant = SakanaAssistant(self.config)
        # Initialize assistant BEFORE starting any interface (ensures memory_manager, plugins, etc.)
        await self.assistant.initialize()
        # Align learning flag with config (if present)
        try:
            self.assistant.learning_enabled = bool(getattr(self.config, 'learning_enabled', True))
        except Exception:
            pass
        
        if self.config.enable_gui:
            try:
                from src.ui.gui_interface import GUIInterface, set_data_directories
                # Configure data directories for GUI components
                set_data_directories(DATA_DIR, LOGS_DIR, SESSIONS_DIR, TMP_DIR)
                self.interface = GUIInterface(self.assistant)
                await self.interface.initialize()
                # Log actual bound host:port (port may fall back)
                host = getattr(self.interface, 'host', '127.0.0.1')
                port = getattr(self.interface, 'port', 8765)
                logger.info("GUI interface initialized; open http://%s:%d/", host, port)
                logger.info("Assistant ready!")
                return
            except Exception as e:
                logger.error(f"Failed to initialize GUI: {e}. Falling back to CLI.")
        
        # Fallback to CLI
        self.interface = CLIInterface(self.assistant)
        await self.interface.initialize()
        logger.info("CLI interface initialized")
        logger.info("Assistant ready!")
    
    async def run(self):
        """Run the assistant"""
        
        self.running = True
        
        # Print welcome message
        print("\n" + "="*60)
        print("*** Sakana Desktop Assistant ***")
        print("Self-learning AI that adapts to your needs")
        print("="*60)
        print("\nCommands:")
        print("  /help     - Show available commands")
        print("  /plugins  - List loaded plugins")
        print("  /stats    - Show learning statistics")
        print("  /exit     - Exit the assistant")
        print("\nType your message or command...\n")
        
        try:
            # Run the interface
            await self.interface.run()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the assistant gracefully"""
        
        if not self.running:
            return
        
        self.running = False
        logger.info("Shutting down assistant...")
        
        if self.interface:
            await self.interface.shutdown()
        
        if self.assistant:
            await self.assistant.shutdown()
        
        logger.info("Shutdown complete")
    
    def handle_signal(self, sig, frame):
        """Handle system signals"""
        
        logger.info(f"Received signal {sig}")
        asyncio.create_task(self.shutdown())

async def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(description="Sakana Desktop Assistant")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file"
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Disable GUI and use CLI only"
    )
    parser.add_argument(
        "--learning",
        choices=["on", "off"],
        default="on",
        help="Enable/disable self-learning"
    )
    
    args = parser.parse_args()
    
    # Determine config path - use provided path or default to config.yaml in project root
    config_path = args.config
    if not config_path:
        # Default to config.yaml in project root
        project_root = Path(__file__).parent.parent
        default_config = project_root / "config.yaml"
        if default_config.exists():
            config_path = default_config
        else:
            pass  # Use defaults
    
    # Create runner
    runner = AssistantRunner(config_path)
    
    # Override config with command line args
    if args.no_gui:
        runner.config.enable_gui = False
    
    if args.learning == "off":
        runner.config.learning_enabled = False
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, runner.handle_signal)
    signal.signal(signal.SIGTERM, runner.handle_signal)
    
    # Initialize and run
    await runner.initialize()
    await runner.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)