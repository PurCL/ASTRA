import json 
import uuid
import os
import sys
import json
import tempfile
import shutil
import traceback
import logging
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm


# Add the parent directory to the path to import the module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from temporal_explorator import get_next_attack_prompt, reset_explorer
from temporal_explorator.models.state import State
from temporal_explorator.models.action import Action
from temporal_explorator.config import get_config
from temporal_explorator.utils.logger import logger, purcl_logger_adapter, update_session_info


# def load_data(data_dir="/data4/user/shen447/amazon_code_challenge/amazon-cobot-code/purcl_attacker/t3_malware_probing_agent/data"):
#     data = []
#     for file in os.listdir(data_dir):
#         if file.endswith(".json"):
#             with open(os.path.join(data_dir, file), "r") as f:
#                 raw_data = json.load(f)
#                 for item in raw_data:
#                     if item["prompt_type"] == "MaliciousGoal":
#                         goal = item["prompt"]
#                         break
                
#                 for item in raw_data:
#                     if "seedprompt" in item["prompt_type"].lower() and "benign" not in item["prompt_type"].lower():
#                         seed_prompt = item["prompt"]
#                         data.append({
#                             "goal": goal,
#                             "seed_prompt": seed_prompt,
#                         })
#     return data


def load_data(data_filepath="/data4/user/shen447/amazon_code_challenge/astra-share/data_out/syn_sec_event_tasks.jsonl"):
    data = []
    with open(data_filepath, "r") as f:
        for line in f:
            raw_data = json.loads(line)
            succ_tasks = raw_data["succ_tasks"]
            all_triggered_examples_w_reasoning = raw_data["all_triggered_examples_w_reasoning"]
            for task in succ_tasks:
                for example in all_triggered_examples_w_reasoning:
                    if example["task"] == task:
                        goal = example["goal"]
                        break
                data.append({
                    "goal": goal,
                    "seed_prompt": task,
                })
    
    print(f"number of data: {len(data)}")
    return data




class TestTemporalExploratorIntegration:
    """Integration test class for the Temporal Explorator module."""

    def load_data(self, data_dir="/data4/user/shen447/amazon_code_challenge/astra-share/data_out/syn_sec_event_tasks.jsonl"):
        """Load test data from the specified directory."""
        self.data = load_data(data_dir)
        purcl_logger_adapter.info(f"Loaded {len(self.data)} test cases from {data_dir}")
        for i, item in enumerate(self.data):
            purcl_logger_adapter.debug(f"Test case {i}: goal='{item['goal'][:50]}...', seed_prompt='{item['seed_prompt'][:50]}...'")
    
    
    def setup_method(self):
        """Set up test environment before each test method."""
        purcl_logger_adapter.info("Setting up test environment")
        
        # Load test data if not already loaded
        if not hasattr(self, 'data') or not self.data:
            self.load_data()
        
        
        self.bt_config = {
            # "model_url": "http://54.202.245.166:8010/v1",
            # "model_api_key": "reverse-training",
            # "model_name": "llama-3.1-70b-inst-judge",
            "model_url": "http://54.212.178.87:8010/v1",
            "model_api_key": "astra",
            "model_name": "qwen-2.5-coder-7b-instruct",
            "temperature": 0.7,
            "max_tokens": 1024,
            "max_retries": 5,
        }

        # Test configuration
        self.config = {
            # State mapper configuration
            "state_mapper": {
                "model_url": "http://35.87.6.13:8000/v1",
                "model_api_key": "redteam233",
                "model_name": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
                "temperature": 0.7,
                "max_tokens": 1024,
                "max_retries": 5
            },
            
            # Action selector configuration
            "action_selector": {
                "action_selection_strategy": "deterministic"
            },
            
            # Prompt generator configuration
            "prompt_generator": {
                "mutator_model_url": "http://35.87.6.13:8000/v1",
                "mutator_model_api_key": "redteam233",
                "mutator_model_name_or_path": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
                "mutator_model_temperature": 0.7,
                "mutator_model_max_tokens": 1024,
                "mutator_model_max_retries": 5
            }
        }
        
        # Test data - will be set per session
        # self.test_bt_id = "llama-3.1-70b-inst"
        self.test_bt_id = "qwen-2.5-coder-7b-instruct"
        # self.test_bt_id = "purpcode-14b-rl"
        # self.test_bt_id = "llama-3-8b-instruct-cb"

        self.note = "new-agent-prompt-150"

        # Create a temporary directory for test sessions
        # put the test dir in the current directory
        self.test_dir = os.path.join(os.path.dirname(__file__), "session_data", self.test_bt_id, self.note)
        purcl_logger_adapter.debug(f"Test directory: {self.test_dir}")
        
        # Ensure test directory exists
        os.makedirs(self.test_dir, exist_ok=True)
        purcl_logger_adapter.debug("Test directory created/verified")
    
    def teardown_method(self):
        """Clean up test environment after each test method."""
        purcl_logger_adapter.info("Cleaning up test environment")
        
        # Remove temporary directory
        # if os.path.exists(self.test_dir):
        #     logger.debug(f"Removing test directory: {self.test_dir}")
        #     shutil.rmtree(self.test_dir)
        # else:
        #     logger.debug("Test directory does not exist, skipping cleanup")
    

    
    def test_multiple_sessions(self):
        """Test multiple sessions, each with a different seed prompt and goal from self.data."""
        purcl_logger_adapter.info("\n=== Testing Multiple Sessions ===")
        
        if not self.data:
            purcl_logger_adapter.error("No test data available. Please load data first.")
            return
        
        MAX_TURNS = 5  # Each session has at most 5 turns
        MAX_SESSIONS = len(self.data)  # Test up to 5 sessions or all available data
        
        purcl_logger_adapter.info(f"Testing {MAX_SESSIONS} sessions, each with up to {MAX_TURNS} turns")
        
        session_results = []
        
        for session_idx in tqdm(range(MAX_SESSIONS)):
            test_case = self.data[session_idx]
            session_id = str(uuid.uuid4())
            
            purcl_logger_adapter.info(f"\n{'='*80}")
            purcl_logger_adapter.info(f"🔄 Session {session_idx + 1}/{MAX_SESSIONS}")
            purcl_logger_adapter.info(f"📋 Session ID: {session_id}")
            purcl_logger_adapter.info(f"🎯 Goal: {test_case['goal'][:100]}...")
            purcl_logger_adapter.info(f"💬 Seed Prompt: {test_case['seed_prompt'][:100]}...")
            purcl_logger_adapter.info(f"{'='*80}")
            
            # Update logger with current session information
            update_session_info(self.test_bt_id, session_id)

            
            current_chat_history = []
            seed_prompt = test_case['seed_prompt']
            goal = test_case['goal']

            response = self._get_real_model_response(seed_prompt, current_chat_history)

            current_chat_history.extend([
                {"role": "user", "content": seed_prompt},
                {"role": "assistant", "content": response}
            ])
            
            session_result = {
                "session_idx": session_idx,
                "session_id": session_id,
                "goal": test_case['goal'],
                "seed_prompt": test_case['seed_prompt'],
                "turns_completed": 0,
                "final_state": None,
                "success": False,
                "error": None
            }
            
            try:
                # Each session can have up to MAX_TURNS additional turns (beyond the initial seed prompt)
                for turn in range(1, MAX_TURNS + 1):
                    purcl_logger_adapter.info(f"\n🔄 Turn {turn}/{MAX_TURNS}")
                    
                    # Generate next prompt for this session
                    prompt, state = get_next_attack_prompt(
                        bt_id=self.test_bt_id,
                        session_id=session_id,
                        chat_history=current_chat_history,
                        goal=test_case['goal'],
                        config=self.config,
                        save_dir=self.test_dir
                    )
                    
                    if state == State.JAILBROKEN:
                        purcl_logger_adapter.info("   🎯 Jailbroken! Session successful!")
                        session_result["final_state"] = "JAILBROKEN"
                        session_result["success"] = True
                        break
                    
                    if state == State.ABORT:
                        purcl_logger_adapter.info("   ⚠️ Abort! Session failed.")
                        session_result["final_state"] = "ABORT"
                        session_result["success"] = False
                        break
                    
                    purcl_logger_adapter.info(f"✅ Turn {turn} prompt: {prompt[:100]}...")
                    
                    # Get real model response with full chat history
                    response = self._get_real_model_response(prompt, current_chat_history)
                    purcl_logger_adapter.info(f"🤖 Turn {turn} model response: {response[:100]}...")
                    
                    # Update chat history for next turn
                    current_chat_history.extend([
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": response}
                    ])
                    
                    session_result["turns_completed"] = turn
                    purcl_logger_adapter.info(f"📊 Chat history length after turn {turn}: {len(current_chat_history)}")
                
                # If we completed all turns without jailbreaking or aborting
                if session_result["final_state"] is None:
                    session_result["final_state"] = "COMPLETED"
                    session_result["success"] = True
                
                purcl_logger_adapter.info(f"✅ Session {session_idx + 1} completed successfully")
                
            except Exception as e:
                purcl_logger_adapter.error(f"❌ Session {session_idx + 1} failed: {e}")
                purcl_logger_adapter.error("📋 Full traceback:")
                traceback.print_exc()
                session_result["error"] = str(e)
                session_result["success"] = False
            
            session_results.append(session_result)
            
            # Reset explorer for next session
            try:
                reset_explorer()
                purcl_logger_adapter.info(f"🔄 Reset explorer for session {session_id}")
            except Exception as e:
                purcl_logger_adapter.warning(f"⚠️ Failed to reset explorer for session {session_id}: {e}")
        
        # Print summary
        self._print_session_summary(session_results)
        
        # Return success if at least one session succeeded
        successful_sessions = [r for r in session_results if r["success"]]
        return len(successful_sessions) > 0
    
    def _print_session_summary(self, session_results: List[Dict[str, Any]]):
        """Print a summary of all session results."""
        purcl_logger_adapter.info("\n" + "="*80)
        purcl_logger_adapter.info("📊 SESSION SUMMARY")
        purcl_logger_adapter.info("="*80)
        
        total_sessions = len(session_results)
        successful_sessions = [r for r in session_results if r["success"]]
        failed_sessions = [r for r in session_results if not r["success"]]
        
        purcl_logger_adapter.info(f"📈 Total Sessions: {total_sessions}")
        purcl_logger_adapter.info(f"✅ Successful: {len(successful_sessions)}")
        purcl_logger_adapter.info(f"❌ Failed: {len(failed_sessions)}")
        purcl_logger_adapter.info(f"📊 Success Rate: {len(successful_sessions)/total_sessions*100:.1f}%")
        
        # Summary by final state
        state_counts = {}
        for result in session_results:
            state = result["final_state"]
            state_counts[state] = state_counts.get(state, 0) + 1
        
        purcl_logger_adapter.info("\n📋 Final States:")
        for state, count in state_counts.items():
            purcl_logger_adapter.info(f"   {state}: {count}")
        
        # Average turns completed
        avg_turns = sum(r["turns_completed"] for r in session_results) / total_sessions
        purcl_logger_adapter.info(f"\n🔄 Average Turns Completed: {avg_turns:.1f}")
        
        # Detailed results
        purcl_logger_adapter.info("\n📝 Detailed Results:")
        for i, result in enumerate(session_results):
            status = "✅" if result["success"] else "❌"
            purcl_logger_adapter.info(f"   {status} Session {i+1}: {result['final_state']} ({result['turns_completed']} turns)")
            if result["error"]:
                purcl_logger_adapter.info(f"      Error: {result['error']}")
        
        purcl_logger_adapter.info("="*80)
    
    def _get_real_model_response(self, prompt: str, chat_history: List[Dict[str, str]] = None) -> str:
        """Get a real response from the model."""
        try:
            from openai import OpenAI
            
            client = OpenAI(
                base_url=self.bt_config["model_url"],
                api_key=self.bt_config["model_api_key"]
            )
            
            # Prepare messages - include full chat history if provided
            if chat_history:
                messages = chat_history + [{"role": "user", "content": prompt}]
            else:
                messages = [{"role": "user", "content": prompt}]
            
            response = client.chat.completions.create(
                model=self.bt_config["model_name"],
                messages=messages,
                temperature=self.bt_config["temperature"],
                max_tokens=self.bt_config["max_tokens"]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            purcl_logger_adapter.info(f"⚠️ Failed to get real model response: {e}")
            purcl_logger_adapter.info("📋 Full traceback:")
            traceback.print_exc()
            # Fallback to simulated response
            return "I understand your request, but I need to ensure this is for legitimate purposes. Could you provide more context about your use case?"


def run_integration_tests():
    """Run all integration tests."""
    purcl_logger_adapter.info("🚀 Starting Temporal Explorator Integration Tests")
    purcl_logger_adapter.info("=" * 60)
    
    test_instance = TestTemporalExploratorIntegration()
    
    # Run all test methods
    test_methods = [
        test_instance.test_multiple_sessions,
        # test_instance.test_basic_integration,
        # test_instance.test_explorer_management,
        # test_instance.test_session_persistence,
        # test_instance.test_different_states,
        # test_instance.test_error_handling,
        # test_instance.test_full_conversation_flow
    ]
    
    passed = 0
    failed = 0
    
    for test_method in test_methods:
        try:
            test_instance.setup_method()
            test_method()
            test_instance.teardown_method()
            passed += 1
            purcl_logger_adapter.info(f"✅ {test_method.__name__} PASSED")
        except Exception as e:
            failed += 1
            purcl_logger_adapter.info(f"❌ {test_method.__name__} FAILED: {e}")
            purcl_logger_adapter.info("📋 Full traceback:")
            traceback.print_exc()
            try:
                test_instance.teardown_method()
            except:
                pass
            
            # Exit on first failure
            purcl_logger_adapter.info(f"\n💥 Test failed at {test_method.__name__}. Exiting...")
            purcl_logger_adapter.info("=" * 60)
            purcl_logger_adapter.info(f"📊 Test Results: {passed} passed, {failed} failed")
            return False
    
    purcl_logger_adapter.info("\n" + "=" * 60)
    purcl_logger_adapter.info(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        purcl_logger_adapter.info("🎉 All tests passed!")
        return True
    else:
        purcl_logger_adapter.info("💥 Some tests failed!")
        return False


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1) 