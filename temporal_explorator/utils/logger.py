import logging
import os
from pathlib import Path

# Create log directory if it doesn't exist
log_dir = Path(__file__).parent.parent.parent / "tests" / "log"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "qwen-2.5-coder-7b-instruct-new-agent-prompt-150.log"

# Configure the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s')

logging.getLogger("httpx").setLevel(logging.WARNING)

purcl_logger = logging.getLogger("purcl_logger")
purcl_logger.setLevel(logging.INFO)
purcl_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(pair_id)s#%(session_id)s - %(filename)s:%(lineno)d - %(funcName)s - %(message)s"
)

# Clear existing handlers for purcl_logger
purcl_logger.handlers.clear()

# Create file handler for purcl_logger
purcl_file_handler = logging.FileHandler(log_file)
purcl_file_handler.setFormatter(purcl_formatter)
purcl_logger.addHandler(purcl_file_handler)
purcl_logger.propagate = False

purcl_logger_extra = {
    'pair_id': 'TBD-pair_id',
    'session_id': 'TBD-session_id',
}
purcl_logger_adapter = logging.LoggerAdapter(purcl_logger, purcl_logger_extra)

def update_session_info(pair_id: str, session_id: str):
    """Update the session information in the logger."""
    global purcl_logger_extra, purcl_logger_adapter
    purcl_logger_extra.update({
        'pair_id': pair_id,
        'session_id': session_id,
    })
    # Create a new adapter with updated extra info
    purcl_logger_adapter = logging.LoggerAdapter(purcl_logger, purcl_logger_extra)

# Export the variables for external use
__all__ = ['logger', 'purcl_logger', 'purcl_logger_adapter', 'purcl_logger_extra', 'update_session_info']