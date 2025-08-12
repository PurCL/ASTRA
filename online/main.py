import json
# from tests import bt_stub
from tests import example_bt as bt_stub
import uuid
from tqdm import tqdm
from rt import rt_entry
import argparse

parser = argparse.ArgumentParser(description="Run the red team simulation.")
parser.add_argument("--pair_id", type=str, default="astra-vs-phi4m")
parser.add_argument("--log", type=str, default="")

args = parser.parse_args()

def main():
    pair_id = args.pair_id
    if args.log:
        fout_name = args.log
    else:
        fout_name = f"log_out/{pair_id}.jsonl"
    fout = open(fout_name, "w")
    N_SESSION = 50
    N_PROBING = 25
    N_TURN = 5
    for session_num in tqdm(range(N_SESSION), desc="Testing..."):
        session_id = str(uuid.uuid4())
        id_to_query = f"{pair_id}#~#{session_id}"
        # simulate RT        
        messages = []
        for turn_num in range(N_TURN):
            rt_rsp = rt_entry.handle_chat_request(
                messages=messages,
                pair_id=pair_id,
                session_id=session_id,
                is_probing=session_num < N_PROBING,
                is_finished=False,
            )
            print(f"RT response: {rt_rsp[:100]}")
            if rt_rsp == "<Jailbroken>":
                break

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
            pair_id=pair_id,
            session_id=session_id,
            is_probing=session_num < N_PROBING,
            is_finished=True,
        )
        fout.write(json.dumps({
            'session_id': session_id,
            'red_team_id': pair_id,
            'messages': messages,
        }) + "\n")
        fout.flush()

    fout.close()


if __name__ == "__main__":
    main()
