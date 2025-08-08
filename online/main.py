from tests import bt_stub
import uuid
from tqdm import tqdm
from rt import rt_entry


def main():
    rt_id = "purcl_test_rt"
    N_SESSION = 200
    N_PROBING = 50
    N_TURN = 5
    for session_num in tqdm(range(N_SESSION), desc="Testing..."):
        session_id = str(uuid.uuid4())
        id_to_query = f'{rt_id}#~#{session_id}'
        # simulate RT
        messages = []
        for turn_num in range(N_TURN):
            rt_rsp = rt_entry.handle_chat_request(
                messages=messages,
                red_team_id=rt_id,
                session_id=session_id,
                is_probing=session_num < N_PROBING,
                is_finished=False
            )
            messages.append({
                "role": "attacker",
                "content": rt_rsp,                
            })
            bt_rsp = bt_stub.handle_chat_request(
                messages=messages,
                red_team_id=id_to_query
            )
            messages.append({
                "role": "defender",
                "content": bt_rsp,
            })
        # simulate end of session
        _ = rt_entry.handle_chat_request(
            messages=messages,
            red_team_id=rt_id,
            session_id=session_id,
            is_probing=session_num < N_PROBING,
            is_finished=True
        )



        





if __name__ == "__main__":
    main()