import json
from bt.client import BTClientFactory
import uuid
from tqdm import tqdm
from rt import rt_entry
import argparse
import yaml

parser = argparse.ArgumentParser(description="Run the red team simulation.")
parser.add_argument("--model_name", type=str, default="phi4m", help="Name of the model to use as defender")
parser.add_argument("--system_name", type=str, default="astra", help="Name of the red team system")
parser.add_argument("--note", type=str, default="", help="Optional note to add to the pair ID")
parser.add_argument("--config", type=str, default="resources/client-config.yaml", help="Path to client configuration file")
parser.add_argument("--log", type=str, default="", help="Path to output log file (defaults to log_out/{pair_id}.jsonl)")
parser.add_argument("--n_session", type=int, default=200, help="Number of chat sessions to simulate")
parser.add_argument("--n_probing", type=int, default=100, help="Number of initial sessions used for probing")
parser.add_argument("--n_turn", type=int, default=5, help="Maximum number of turns per chat session")
args = parser.parse_args()

def main():
    if args.note:
        pair_id = f"{args.system_name}-vs-{args.model_name}-{args.note}"
    else:
        pair_id = f"{args.system_name}-vs-{args.model_name}"
    config = yaml.safe_load(open(args.config, "r"))
    client_config = config[args.model_name]
    bt_entry = BTClientFactory.create_client(
        client_name=client_config["model_name"],
        **client_config,
    )
    bt_entry.test_client()

    if args.log:
        fout_name = args.log
    else:
        fout_name = f"log_out/{pair_id}.jsonl"
    fout = open(fout_name, "w")
    N_SESSION = args.n_session
    N_PROBING = args.n_probing
    N_TURN = args.n_turn
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
            bt_rsp = bt_entry.handle_chat_request(
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
