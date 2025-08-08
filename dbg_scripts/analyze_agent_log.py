import json
from tqdm import tqdm
from transformers import AutoTokenizer
import os

re_log = [json.loads(line) for line in open("log_out/syn_sec_event.log")]

re_log = [e for e in re_log if 'msg' in e and "IGNORE-LOG" not in e["msg"] and "SEND" in e["msg"]]



# parse timestamp from string to utc seconds
import datetime


def parse_time_str_to_utc_seconds(time_str):
    dt = datetime.datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    utc_seconds = (dt - datetime.datetime(1970, 1, 1)).total_seconds()
    return utc_seconds


parsed_re_log = []
for entry in tqdm(re_log):
    time = entry["time"]
    timestamp = parse_time_str_to_utc_seconds(time)
    if "msg" in entry:
        entry = json.loads(entry["msg"])
    else:
        entry = entry
    if "SEND" not in entry["delivery_stage"]:
        continue
    payload_str = entry["payload"]
    payload = json.loads(payload_str)
    entry["parsed_payload"] = payload
    ret_entry = {
        "time": time,
        "timestamp": timestamp,
        "parsed_payload": payload,
    }
    parsed_re_log.append(ret_entry)


session_id2entries = {}
for entry in parsed_re_log:
    if "session_id" not in entry["parsed_payload"]:
        continue
    session_id = entry["parsed_payload"]["session_id"]
    if session_id not in session_id2entries:
        session_id2entries[session_id] = []
    session_id2entries[session_id].append(entry)


############################################################
# specific for coding task composer
############################################################

finished_entries = []
for sid, entries in session_id2entries.items():
    if len(entries) < 2:
        continue
    if "GenResult" in entries[-1]["parsed_payload"]["type_name"]:
        finished_entries.append(entries)


interesting_entries = []
for sid, entries in session_id2entries.items():
    first_timestamp = entries[0]["timestamp"]
    time_cut_off = parse_time_str_to_utc_seconds("2025-06-15 3:05:00")
    if first_timestamp > time_cut_off:
        interesting_entries.append(entries)


print()