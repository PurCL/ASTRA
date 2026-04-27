from agent_sec_composer.output_parser import parse_final_case_xml
import json
from tqdm import tqdm
import argparse


def main():
    parser = argparse.ArgumentParser(description="Parse agent security test cases from JSONL output")
    parser.add_argument("--input", "-i", required=True, help="Input JSONL file path")
    parser.add_argument("--output", "-o", required=True, help="Output JSONL file path")
    args = parser.parse_args()

    fin_lines = open(args.input, "r").readlines()
    fout = open(args.output, "w")
    succ_cnt = 0
    for line in tqdm(fin_lines, desc="Parsing final cases"):
        entry = json.loads(line)
        final_output = entry["final_output"]
        message_history = entry["message_history"]
        # extract <final_case>...</final_case> from final_output
        if "<final_case>" not in final_output or "</final_case>" not in final_output:
            continue
        final_case_xml = final_output.split("<final_case>")[1].split("</final_case>")[0].strip()
        final_case_xml = f"<final_case>{final_case_xml}</final_case>"
        try:
            final_case = parse_final_case_xml(final_case_xml)
            fout.write(json.dumps(final_case.model_dump()) + "\n")
            succ_cnt += 1
        except Exception as e:
            print(f"Error parsing final case: {e}")
            continue
    print(f"Successfully parsed {succ_cnt} final cases")
    fout.close()


if __name__ == "__main__":
    main()