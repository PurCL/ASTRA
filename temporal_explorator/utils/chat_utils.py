from openai import OpenAI
from typing import List, Dict
import re


def chat_with_model(
    model_client: OpenAI,
    model_name_or_path: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
    messages: List[Dict[str, str]]
) -> str:
    response = None
    for retry in range(max_retries):
        try:
            raw_response = model_client.chat.completions.create(
                model=model_name_or_path,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            response = raw_response.choices[0].message.content
            break
        except Exception as e:
            if retry == max_retries - 1:
                raise e
            else:
                print(f"Retry {retry + 1}/{max_retries} failed: {str(e)}")
                continue
    return response


def extract_tag(text: str, tag_name: str) -> str:
    start_tag = "<" + tag_name + ">"
    end_tag = "</" + tag_name + ">"
    if not (start_tag in text and end_tag in text):
        #quick fix: try to match the patten ### State 
        pattern = r"###\s*State\s*(.*?)\s*###\s*Reasoning\s*(.*?)"
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
        return None
    start_idx = text.index(start_tag) + len(start_tag)
    remaining_text = text[start_idx:]
    end_idx = remaining_text.index(end_tag)
    return remaining_text[:end_idx].strip()