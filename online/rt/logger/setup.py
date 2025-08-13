import logging

# Configure the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Optionally, set a specific format for the logs
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Apply the formatter to all existing handlers (like the default CloudWatch handler)
for handler in logger.handlers:
    handler.setFormatter(formatter)

purcl_logger = logging.getLogger("purcl_logger")
purcl_logger.setLevel(logging.INFO)
purcl_formatter = logging.Formatter(
    "%(name)s - %(levelname)s - %(pair_id)s#%(session_id)s - %(message)s"
)
purcl_handler = logging.StreamHandler()
purcl_handler.setFormatter(purcl_formatter)
purcl_logger.addHandler(purcl_handler)
purcl_logger.propagate = False

purcl_logger_extra = {
    'pair_id': 'TBD-pair_id',
    'session_id': 'TBD-session_id',
}
purcl_logger_adapter = logging.LoggerAdapter(purcl_logger, purcl_logger_extra)