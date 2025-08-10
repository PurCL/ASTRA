from typing import List, Dict
from rt.scheduler import DefenderScheduler


defender_id2scheduler = {}

def handle_chat_request(messages: List[Dict[str, str]], red_team_id: str, session_id: str, is_probing:bool, is_finished:bool) -> str:
    if is_finished:
        defender_scheduler = defender_id2scheduler[red_team_id]
        defender_scheduler.finish_attack(session_id, messages)
        return None
    if len(messages) > 0:
        defender_scheduler = defender_id2scheduler[red_team_id]
        return defender_scheduler.continue_attack(session_id, messages)
    else:
        if red_team_id not in defender_id2scheduler:
            scheduler = DefenderScheduler(defender_id=red_team_id)
            defender_id2scheduler[red_team_id] = scheduler
        else:
            scheduler = defender_id2scheduler[red_team_id]
        return scheduler.new_attack(session_id=session_id)