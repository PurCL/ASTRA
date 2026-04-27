import datasets
import json
import argparse


def main():
    parser = argparse.ArgumentParser(description="Upload parsed agent security cases to HuggingFace dataset")
    parser.add_argument("--input", "-i", required=True, help="Input parsed JSONL file path")
    parser.add_argument("--dataset-name", "-d", required=True, help="HuggingFace dataset name (e.g., 'username/dataset-name')")
    args = parser.parse_args()

    data_in = [json.loads(line) for line in open(args.input, "r")]
    dataset_entries = []
    for entry in data_in:
        dataset_entries.append({
            "prohibited_domain": entry["prohibited_domain"],
            "technique_family": entry["technique_family"],
            "concrete_prohibited_instance": entry["concrete_prohibited_instance"],
            "request_text": entry["request_text"],
            "malicious_rationale": entry["malicious_rationale"],
        })
    dataset = datasets.Dataset.from_list(dataset_entries)
    dataset.push_to_hub(args.dataset_name)
    print(f"Successfully uploaded {len(dataset_entries)} entries to {args.dataset_name}")


if __name__ == "__main__":
    main()