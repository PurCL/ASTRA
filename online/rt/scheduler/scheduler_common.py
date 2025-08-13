from typing import Dict, List, Tuple
from rt.data_modeling import SessionDO


class SchedulerBase:

    def new_attack(self, session_id: str) -> Tuple[SessionDO, str]:
        """
        Start a new attack session.
        """
        raise NotImplementedError()
    
    def continue_attack(self, session_id: str, messages: List[Dict[str, str]], session_do: SessionDO) -> str:
        """
        Continue an existing attack session with new messages.
        """
        raise NotImplementedError()
    
    def finish_attack(self, session_id: str, messages: List[Dict[str, str]], session_do: SessionDO) -> str:
        """
        Finish an attack session and return the final response.
        """
        raise NotImplementedError()