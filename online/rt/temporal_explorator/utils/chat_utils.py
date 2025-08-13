from openai import OpenAI
from typing import List, Dict
import re
import traceback
from rt.logger import purcl_logger_adapter
from rt.temporal_explorator.utils.exceptions import ModelCommunicationError, ValidationError

def query_model(
    model_client: OpenAI,
    model_name_or_path: str,
    temperature: float,
    max_tokens: int,
    max_retries: int,
    messages: List[Dict[str, str]],
    tag_names: List[str] = None
) -> Dict[str, str]:
    """
    Query model and optionally extract multiple tags from the response.
    
    Args:
        model_client: OpenAI client instance
        model_name_or_path: Model name or path
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        max_retries: Maximum number of retries
        messages: List of chat messages
        tag_names: Optional list of tag names to extract from response
        
    Returns:
        Dictionary with extracted tags if tag_names is provided, otherwise {"raw": raw_response}
    """
    for retry in range(max_retries):
        try:
            # Validate input parameters
            if not isinstance(model_client, OpenAI):
                raise ValidationError(
                    f"model_client must be an OpenAI instance, got {type(model_client)}",
                    field="model_client",
                    value=type(model_client)
                )
            
            if not isinstance(model_name_or_path, str) or not model_name_or_path.strip():
                raise ValidationError(
                    "model_name_or_path must be a non-empty string",
                    field="model_name_or_path",
                    value=model_name_or_path
                )
            
            if not isinstance(messages, list) or not messages:
                raise ValidationError(
                    "messages must be a non-empty list",
                    field="messages",
                    value=type(messages)
                )
            
            if not isinstance(temperature, (int, float)) or temperature < 0 or temperature > 2:
                raise ValidationError(
                    f"temperature must be a number between 0 and 2, got {temperature}",
                    field="temperature",
                    value=temperature
                )
            
            if not isinstance(max_tokens, int) or max_tokens <= 0:
                raise ValidationError(
                    f"max_tokens must be a positive integer, got {max_tokens}",
                    field="max_tokens",
                    value=max_tokens
                )
            
            if tag_names is not None and not isinstance(tag_names, list):
                raise ValidationError(
                    f"tag_names must be a list or None, got {type(tag_names)}",
                    field="tag_names",
                    value=type(tag_names)
                )
            
            raw_response = model_client.chat.completions.create(
                model=model_name_or_path,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if not raw_response.choices:
                raise ModelCommunicationError(
                    "No choices returned from model",
                    model_name=model_name_or_path,
                    retry_count=retry
                )
            
            response = raw_response.choices[0].message.content
            
            if not response:
                raise ModelCommunicationError(
                    "Empty response from model",
                    model_name=model_name_or_path,
                    retry_count=retry
                )
            
            # If tag extraction is required, try to extract all tags
            if tag_names:
                extracted_tags = {}
                all_tags_extracted = True
                
                for tag_name in tag_names:
                    if not isinstance(tag_name, str):
                        raise ValidationError(
                            f"Tag name must be a string, got {type(tag_name)}",
                            field="tag_name",
                            value=type(tag_name)
                        )
                    
                    extracted_content = extract_tag(response, tag_name)
                    if extracted_content is not None:
                        extracted_tags[tag_name] = extracted_content
                    else:
                        all_tags_extracted = False
                        purcl_logger_adapter.warning(f"Failed to extract tag '{tag_name}' from response")
                
                if all_tags_extracted:
                    return extracted_tags
                else:
                    # Some tag extraction failed, this counts as a retry
                    if retry == max_retries - 1:
                        raise ModelCommunicationError(
                            f"Failed to extract all tags {tag_names} after {max_retries} retries",
                            model_name=model_name_or_path,
                            retry_count=retry
                        )
                    else:
                        purcl_logger_adapter.warning(f"Retry {retry + 1}/{max_retries}: Failed to extract all tags {tag_names} from response")
                        continue
            else:
                # No tag extraction required, return raw response
                return {"raw": response}
                
        except (ValidationError, ModelCommunicationError):
            raise
        except Exception as e:
            if retry == max_retries - 1:
                purcl_logger_adapter.error(f"Final retry failed: {str(e)}")
                purcl_logger_adapter.error(traceback.format_exc())
                raise ModelCommunicationError(
                    f"Unexpected error during model communication: {str(e)}",
                    model_name=model_name_or_path,
                    retry_count=retry
                )
            else:
                purcl_logger_adapter.warning(f"Retry {retry + 1}/{max_retries} failed: {str(e)}")
                continue
    
    raise ModelCommunicationError(
        f"Failed to get valid response after {max_retries} retries",
        model_name=model_name_or_path,
        retry_count=max_retries
    )


def extract_tag(text: str, tag_name: str) -> str:
    """Extract content from XML tags or markdown patterns in text."""
    try:
        # Validate input parameters
        if not isinstance(text, str):
            raise ValidationError(
                f"text must be a string, got {type(text)}",
                field="text",
                value=type(text)
            )
        
        if not isinstance(tag_name, str) or not tag_name.strip():
            raise ValidationError(
                "tag_name must be a non-empty string",
                field="tag_name",
                value=tag_name
            )
        
        if not text.strip():
            raise ValidationError(
                "text cannot be empty or whitespace only",
                field="text",
                value=text
            )
        
        # Try XML tag extraction first
        start_tag = "<" + tag_name + ">"
        end_tag = "</" + tag_name + ">"
        
        if start_tag in text and end_tag in text:
            try:
                start_idx = text.index(start_tag) + len(start_tag)
                remaining_text = text[start_idx:]
                end_idx = remaining_text.index(end_tag)
                extracted_content = remaining_text[:end_idx].strip()
                
                if extracted_content:
                    return extracted_content
                else:
                    purcl_logger_adapter.warning(f"Empty content found in tag '{tag_name}'")
                    return None
                    
            except ValueError as e:
                purcl_logger_adapter.error(f"Error parsing XML tag '{tag_name}': {e}")
                return None
        
        # Fallback: try markdown pattern for specific tags
        if tag_name.lower() == "state":
            pattern = r"###\s*State\s*(.*?)(?:\s*###\s*Reasoning|\s*$)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_content = match.group(1).strip()
                if extracted_content:
                    return extracted_content
        
        elif tag_name.lower() == "reasoning":
            pattern = r"###\s*Reasoning\s*(.*?)(?:\s*###\s*State|\s*$)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_content = match.group(1).strip()
                if extracted_content:
                    return extracted_content
        
        elif tag_name.lower() == "prompt":
            pattern = r"###\s*Prompt\s*(.*?)(?:\s*###\s*Reasoning|\s*$)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                extracted_content = match.group(1).strip()
                if extracted_content:
                    return extracted_content
        
        purcl_logger_adapter.debug(f"Tag '{tag_name}' not found in text")
        return None
        
    except ValidationError:
        raise
    except Exception as e:
        purcl_logger_adapter.error(f"Unexpected error in extract_tag: {e}")
        purcl_logger_adapter.error(traceback.format_exc())
        return None