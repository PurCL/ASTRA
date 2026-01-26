from __future__ import annotations

import asyncio
from dataclasses import dataclass

@dataclass
class MainAgentContext:
    instance_id: str
    log_fout_name: str
    composing_agent_history: list[dict[str, str]]