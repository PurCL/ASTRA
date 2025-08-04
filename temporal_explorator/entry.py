from typing import List, Dict
from module.state_mapper import StateMapper
from module.action_selector import ActionSelector
from module.prompt_generator import PromptGenerator


def get_next_attack_prompt(
    bt_id: str,
    session_id: str,
    chat_history: List[Dict[str, str]],
    config: Dict[str, str],
    goal: str|None = None,
) -> str:
    
    assert len(chat_history) >= 2, "chat_history must have at least 2 turns"
    assert len(chat_history) % 2 == 0, "chat_history must have even number of turns"

    if len(chat_history) == 2:
        session_data_dict = [{
            "action": Action.SEND_SEED_PROMPT,
            "prompt": chat_history[0]["content"],
            "response": chat_history[1]["content"],
            "state": State.UNKNOWN,
            "goal": goal,
        }]
    else:
        session_data_dict = json.load(open(f"session_data_{bt_id}_{session_id}.json"))
        session_data_dict[-1]["response"] = chat_history[-1]["content"]

    

    state = map_state(session_data_dict)

    session_data_dict[-1]["state"] = state

    action = select_action(state)
    prompt = generate_prompt(state, action, session_data_dict)
    # mutator = mutator_factory.get_mutator(action)
    

    session_data_dict.append({
        "action": action,
        "prompt": prompt,
        "response": "",
        "state": State.UNKNOWN,
    })

    with open(f"session_data_{bt_id}_{session_id}.json", "w") as f:
        json.dump(session_data_dict, f)

    return prompt