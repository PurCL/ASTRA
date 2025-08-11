import json
from tests import bt_stub
import uuid
from tqdm import tqdm
from rt import rt_entry



def main():
    rt_id = "purcl_test_rt-xxz-0811-0824am"
    fout = open(f"log_out/test_log_{rt_id}.jsonl", "w")
    N_SESSION = 200
    N_PROBING = 50
    N_TURN = 5
    for session_num in tqdm(range(N_SESSION), desc="Testing..."):
        session_id = str(uuid.uuid4())
        id_to_query = f"{rt_id}#~#{session_id}"
        # simulate RT        
        messages = []
        for turn_num in range(N_TURN):
            rt_rsp = rt_entry.handle_chat_request(
                messages=messages,
                red_team_id=rt_id,
                session_id=session_id,
                is_probing=session_num < N_PROBING,
                is_finished=False,
            )
            print(f"RT response: {rt_rsp[:100]}")
            messages.append(
                {
                    "role": "attacker",
                    "content": rt_rsp,
                }
            )
            bt_rsp = bt_stub.handle_chat_request(
                messages=messages, red_team_id=id_to_query
            )
            print(f"BT response: {bt_rsp[:100]}")
            messages.append(
                {
                    "role": "defender",
                    "content": bt_rsp,
                }
            )
        # simulate end of session
        _ = rt_entry.handle_chat_request(
            messages=messages,
            red_team_id=rt_id,
            session_id=session_id,
            is_probing=session_num < N_PROBING,
            is_finished=True,
        )
        fout.write(json.dumps({
            'session_id': session_id,
            'red_team_id': rt_id,
            'messages': messages,
        }) + "\n")
        fout.flush()

    fout.close()


if __name__ == "__main__":
    main()
