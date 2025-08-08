# CUDA_VISIBLE_DEVICES=0,1,2,3,4,5,6,7 vllm serve meta-llama/Llama-3.1-70B-Instruct \
# --served-model-name llama-3.1-70b-inst-judge \
# --port 8010 \
# --host 0.0.0.0 \
# --api-key reverse-training \
# --tensor-parallel-size 8 \
# --chat-template template/llama3.1.jinja \
# --max_model_len 8192 \
# --enforce-eager

CUDA_VISIBLE_DEVICES=6,7 vllm serve Qwen/Qwen2.5-Coder-7B-Instruct \
--served-model-name qwen-2.5-coder-7b-instruct \
--port 8010 \
--host 0.0.0.0 \
--api-key astra \
--tensor-parallel-size 2 \
--max_model_len 8192 \
--enforce-eager

# CUDA_VISIBLE_DEVICES=6,7 vllm serve GraySwanAI/Llama-3-8B-Instruct-RR \
# --served-model-name llama-3-8b-instruct-cb \
# --port 8010 \
# --host 0.0.0.0 \
# --api-key astra \
# --tensor-parallel-size 2 \
# --max_model_len 8192 \
# --enforce-eager



# CUDA_VISIBLE_DEVICES=6,7 vllm serve purpcode/purpcode-14b-rl \
# --served-model-name purpcode-14b-rl \
# --port 8010 \
# --host 0.0.0.0 \
# --api-key astra \
# --tensor-parallel-size 2 \
# --max_model_len 8192 \
# --enforce-eager