"""
Core TemporalExplorator class for managing multi-turn conversations.
"""

import json
import traceback
from typing import List, Dict, Optional, Any
from pathlib import Path

from rt.temporal_explorator.models.state import State
from rt.temporal_explorator.models.action import Action
from rt.temporal_explorator.core.state_mapper import StateMapper
from rt.temporal_explorator.core.action_selector import ActionSelector
from rt.temporal_explorator.core.prompt_generator import PromptGenerator
from rt.logger import purcl_logger_adapter
from rt.temporal_explorator.utils.exceptions import (
    ValidationError,
    SessionError,
    StateMappingError,
    PromptGenerationError,
    FileOperationError,
    ConfigurationError,
)



class TemporalExplorator:
    """
    Main class for managing temporal exploration in multi-turn conversations.
    
    This class orchestrates the entire process of:
    1. State mapping based on conversation history
    2. Action selection based on current state
    3. Prompt generation for the next turn
    4. Session management and persistence
    """
    
    def __init__(self, config: Dict[str, Any], save_dir: str = "sessions"):
        """
        Initialize the TemporalExplorator.
        
        Args:
            config: Configuration dictionary containing all necessary parameters
            save_dir: Directory to save session files (default: "sessions")
        """
        purcl_logger_adapter.info(f"Initializing TemporalExplorator with save_dir: {save_dir}")
        purcl_logger_adapter.info(f"Config keys: {list(config.keys())}")
        
        self.config = config
        self.save_dir = Path(save_dir)
        
        # Create save directory if it doesn't exist
        self.save_dir.mkdir(parents=True, exist_ok=True)
        purcl_logger_adapter.info(f"Save directory created/verified: {self.save_dir}")
        
        # Initialize core components
        purcl_logger_adapter.info("Initializing StateMapper...")
        self.state_mapper = StateMapper(config.get("state_mapper", {}))
        
        purcl_logger_adapter.info("Initializing ActionSelector...")
        self.action_selector = ActionSelector(config.get("action_selector", {}))
        
        purcl_logger_adapter.info("Initializing PromptGenerator...")
        self.prompt_generator = PromptGenerator(config.get("prompt_generator", {}))
        
    
    def process_turn(
        self,
        bt_id: str,
        session_id: str,
        chat_history: List[Dict[str, str]],
        goal: str,
    ) -> str:
        """
        Process a single turn in the conversation.
        
        Args:
            bt_id: Backend target ID
            session_id: Session identifier
            chat_history: List of chat messages in format [{"role": str, "content": str}]
            goal: Optional goal for the session
            
        Returns:
            Generated prompt for the next turn
        """
        session_key = f"{bt_id}_{session_id}"
        purcl_logger_adapter.info(f"Processing turn for session: {session_key}")
        purcl_logger_adapter.info(f"Chat history length: {len(chat_history)}")
        purcl_logger_adapter.info(f"Goal: {goal}")
        
        purcl_logger_adapter.info(f"Processing turn for session {bt_id}_{session_id}")
        
        # Validate input
        purcl_logger_adapter.info("Validating chat history...")
        self._validate_chat_history(chat_history)
        
        # Get or create session
        purcl_logger_adapter.info("Getting or creating session...")
        session_data = self._get_or_create_session(bt_id, session_id)
        
        # Update session with latest response
        purcl_logger_adapter.info("Updating session with latest response...")
        self._update_session_with_response(session_data, chat_history, goal)
        
        # Map current state
        purcl_logger_adapter.info("Mapping current state...")
        current_state = self._map_current_state(session_data)
        purcl_logger_adapter.info(f"Mapped to state: {current_state}")
        if current_state == State.JAILBROKEN:
            # Persist session data
            purcl_logger_adapter.info("Jailbroken! Exiting...")
            self._persist_session(session_data, bt_id, session_id)
            return f"<{State.JAILBROKEN.value}>", current_state
        
        # Select next action
        purcl_logger_adapter.info("Selecting next action...")
        next_action = self._select_next_action(current_state)
        purcl_logger_adapter.info(f"Selected action: {next_action}")
        
        # Generate prompt
        next_prompt = self._generate_prompt(current_state, next_action, session_data)
        
        # Record the turn
        self._record_turn(session_data, next_action, next_prompt, current_state)
        
        # Persist session data
        self._persist_session(session_data, bt_id, session_id)
        
        return next_prompt, current_state
    
    def _validate_chat_history(self, chat_history: List[Dict[str, str]]) -> None:
        """Validate the chat history format and length."""
        
        try:
            if not isinstance(chat_history, list):
                raise ValidationError(
                    f"Chat history must be a list, got {type(chat_history)}",
                    field="chat_history",
                    value=type(chat_history)
                )
            
            if len(chat_history) < 2:
                raise ValidationError(
                    f"Chat history must have at least 2 turns, got: {len(chat_history)}",
                    field="chat_history_length",
                    value=len(chat_history)
                )
            
            if len(chat_history) % 2 != 0:
                raise ValidationError(
                    f"Chat history must have even number of turns, got: {len(chat_history)}",
                    field="chat_history_length",
                    value=len(chat_history)
                )
            
            # Validate format
            for i, message in enumerate(chat_history):
                purcl_logger_adapter.debug(f"Validating message {i}: {type(message)}")
                if not isinstance(message, dict):
                    raise ValidationError(
                        f"Message at index {i} must be a dictionary, got {type(message)}",
                        field=f"message_{i}_type",
                        value=type(message)
                    )
                
                if "content" not in message:
                    raise ValidationError(
                        f"Message at index {i} must contain 'content' field",
                        field=f"message_{i}_content",
                        value=message
                    )
                
                if not isinstance(message["content"], str):
                    raise ValidationError(
                        f"Message content at index {i} must be a string, got {type(message['content'])}",
                        field=f"message_{i}_content_type",
                        value=type(message["content"])
                    )
            
            purcl_logger_adapter.info("Chat history validation passed")
            
        except ValidationError:
            raise
        except Exception as e:
            purcl_logger_adapter.error(f"Unexpected error during chat history validation: {e}")
            purcl_logger_adapter.error(traceback.format_exc())
            raise ValidationError(f"Unexpected error during validation: {str(e)}")
    
    def _get_or_create_session(
        self,
        bt_id: str,
        session_id: str,
    ) -> List[Dict[str, Any]]:
        """Get existing session or create a new one."""
        session_key = f"{bt_id}_{session_id}"
        purcl_logger_adapter.info(f"Getting or creating session: {session_key}")
        
        try:
            # Validate input parameters
            if not isinstance(bt_id, str) or not bt_id.strip():
                raise ValidationError("bt_id must be a non-empty string", field="bt_id", value=bt_id)
            
            if not isinstance(session_id, str) or not session_id.strip():
                raise ValidationError("session_id must be a non-empty string", field="session_id", value=session_id)
            
            # Try to load existing session
            filename = self.save_dir / f"{bt_id}_{session_id}.json"
            purcl_logger_adapter.info(f"Looking for session file: {filename}")
            
            if filename.exists():
                purcl_logger_adapter.info(f"Loading existing session from: {filename}")
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        session_data = json.load(f)
                    
                    if not isinstance(session_data, list):
                        raise ValidationError(
                            f"Session data must be a list, got {type(session_data)}",
                            field="session_data_type",
                            value=type(session_data)
                        )
                    
                    purcl_logger_adapter.info(f"Loaded session with {len(session_data)} entries")
                    return session_data
                    
                except json.JSONDecodeError as e:
                    raise FileOperationError(
                        f"Failed to parse session file: {e}",
                        file_path=str(filename),
                        operation="json_load"
                    )
                except UnicodeDecodeError as e:
                    raise FileOperationError(
                        f"Failed to decode session file: {e}",
                        file_path=str(filename),
                        operation="file_read"
                    )
            
            # Create new session
            purcl_logger_adapter.info(f"Creating new session: {session_key}")
            return []
            
        except (ValidationError, FileOperationError):
            raise
        except Exception as e:
            purcl_logger_adapter.error(f"Unexpected error in session management: {e}")
            purcl_logger_adapter.error(traceback.format_exc())
            raise SessionError(f"Unexpected error in session management: {str(e)}", bt_id=bt_id, session_id=session_id)
    
    def _update_session_with_response(
        self,
        session_data: List[Dict[str, Any]],
        chat_history: List[Dict[str, str]],
        goal: Optional[str] = None
    ) -> None:
        """Update session with the latest model response."""
        if not session_data:
            # First turn - create initial session data
            session_data.append({
                "action": Action.SEND_SEED_PROMPT.value,
                "prompt": chat_history[0]["content"],
                "response": chat_history[1]["content"],
                "state": State.UNKNOWN.value,
                "goal": goal,  # Will be set later
                "internal": [],
            })
        else:
            # Update the last turn with the new response
            session_data[-1]["response"] = chat_history[-1]["content"]
    
    def _map_current_state(self, session_data: List[Dict[str, Any]]) -> State:
        """Map the current conversation state."""
        
        # Get the last turn for state mapping
        last_turn = session_data[-1]
        first_turn = session_data[0]
        
        
        state, reasoning = self.state_mapper.map(
            state=State(last_turn["state"]),
            action=Action(last_turn["action"]),
            prompt=last_turn["prompt"],
            response=last_turn["response"],
            goal=first_turn["goal"],
        )

        
        # Update the last turn's state
        last_turn["state"] = state.value
        last_turn["internal"].append({
            "tool_name": "state_mapper",
            "reasoning": reasoning,
        })
        
        return state
    
    def _select_next_action(self, current_state: State) -> Action:
        """Select the next action based on current state."""
        return self.action_selector.select(current_state)
    
    def _generate_prompt(
        self,
        current_state: State,
        next_action: Action,
        session_data: List[Dict[str, Any]]
    ) -> str:
        """Generate the next prompt based on state and action."""
        # Get the seed prompt (first turn's prompt)
        seed_prompt = session_data[0]["prompt"] if session_data else ""
        
        prompt, reasoning = self.prompt_generator.generate_prompt(
            session_data=session_data,
            action=next_action,
        )

        session_data[-1]["internal"].append({
            "tool_name": "prompt_generator",
            "reasoning": reasoning,
        })
        
        return prompt
    
    def _record_turn(
        self,
        session_data: List[Dict[str, Any]],
        action: Action,
        prompt: str,
        state: State,
    ) -> None:
        """Record a new turn in the session."""
        turn_data = {
            "action": action.value,
            "prompt": prompt,
            "response": "",  # Will be filled in next turn
            "state": State.UNKNOWN.value,  # Will be mapped in next turn
            "internal": [],
        }
        session_data.append(turn_data)
    
    def _persist_session(self, session_data: List[Dict[str, Any]], bt_id: str, session_id: str) -> None:
        """Persist session data to storage."""
        try:
            # Validate input parameters
            if not isinstance(session_data, list):
                raise ValidationError(
                    f"Session data must be a list, got {type(session_data)}",
                    field="session_data",
                    value=type(session_data)
                )
            
            if not isinstance(bt_id, str) or not bt_id.strip():
                raise ValidationError("bt_id must be a non-empty string", field="bt_id", value=bt_id)
            
            if not isinstance(session_id, str) or not session_id.strip():
                raise ValidationError("session_id must be a non-empty string", field="session_id", value=session_id)
            
            filename = self.save_dir / f"{bt_id}_{session_id}.json"
            
            # Ensure the save directory exists
            self.save_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a temporary file first for atomic write
            temp_filename = filename.with_suffix('.tmp')
            
            try:
                with open(temp_filename, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                
                # Atomic move
                temp_filename.replace(filename)
                purcl_logger_adapter.info(f"Session persisted successfully: {filename}")
                
            except (OSError, IOError) as e:
                # Clean up temp file if it exists
                if temp_filename.exists():
                    try:
                        temp_filename.unlink()
                    except OSError:
                        pass
                raise FileOperationError(
                    f"Failed to write session file: {e}",
                    file_path=str(filename),
                    operation="file_write"
                )
                
        except (ValidationError, FileOperationError):
            raise
        except Exception as e:
            purcl_logger_adapter.error(f"Unexpected error during session persistence: {e}")
            purcl_logger_adapter.error(traceback.format_exc())
            raise SessionError(f"Unexpected error during session persistence: {str(e)}", bt_id=bt_id, session_id=session_id)
    
    def get_session_summary(self, bt_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of the session."""
        try:
            filename = self.save_dir / f"{bt_id}_{session_id}.json"
            if not filename.exists():
                return None
            
            with open(filename, 'r') as f:
                session_data = json.load(f)
            
            return {
                "bt_id": bt_id,
                "session_id": session_id,
                "turn_count": len(session_data),
                "current_state": session_data[-1]["state"] if session_data else None,
                "last_action": session_data[-1]["action"] if session_data else None
            }
        except Exception as e:
            purcl_logger_adapter.info(f"Error getting session summary: {e}")
            return None
    
    def reset_session(self, bt_id: str, session_id: str) -> None:
        """Reset a session, clearing all turns."""
        try:
            filename = self.save_dir / f"{bt_id}_{session_id}.json"
            if filename.exists():
                filename.unlink()
            purcl_logger_adapter.info(f"Reset session {bt_id}_{session_id}")
        except Exception as e:
            purcl_logger_adapter.info(f"Error resetting session: {e}") 