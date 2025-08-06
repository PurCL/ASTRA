import json
import logging
from autogen_core.logging import LLMCallEvent, MessageEvent
import time

class MessageLogger(logging.Handler):
    def __init__(self, log_fout):
        super().__init__()
        self.log_out = log_fout

    def emit(self, record: logging.LogRecord):
        try:
            if isinstance(record.msg, MessageEvent) or isinstance(
                record.msg, LLMCallEvent
            ):
                time_stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                if "IGNORE-LOG" in str(record.msg):
                    ret = {
                        "time": time_stamp,
                        "msg": "Skip log due to the IGNORE-LOG marker.",
                    }
                else:
                    ret = {"time": time_stamp, "msg": str(record.msg)}
                self.log_out.write(json.dumps(ret) + "\n")
                self.log_out.flush()
        except Exception as e:
            print("Error in logging: ", e)
            pass