from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import torch, accelerate
import sys
import os
from file_save import save_output_to_file
import time
from huggingface_hub import login

# Load Hugging Face token from environment variable
hf_token = os.getenv("HUGGINGFACE_API_KEY")
login(token=hf_token)

# List of test files from tasks folder
test_file_list = [
    "generative_1.txt",
    "generative_2.txt",
    "generative_3.txt",
    "generative_4.txt",
    "generative_5.txt",
]

if hf_token:
    print("Hugging Face token loaded successfully from environment variable.")
else:
    print("HF_TOKEN environment variable is not set.")

# Models path
model_id = 'meta-llama/Llama-2-7b-chat-hf'

# Adapters path
adapter_id = 'AIRLab-POLIMI/llama-2-7b-chat-hf-btgenbot-adapter'

# Load quantization configuration
quantization_config = BitsAndBytesConfig(load_in_8bit=True)

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    pretrained_model_name_or_path = model_id,
)

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    pretrained_model_name_or_path = model_id,
    quantization_config = quantization_config,
    torch_dtype = torch.float16,
    device_map = "auto",
    trust_remote_code = True,
    token=hf_token,
)

# Define the context for the task
context = "<<SYS>> You will be provided a summary of a task performed by a behavior tree, and your objective is to express this behavior tree in XML format.\n <</SYS>>"

# One-shot example
example_task = """The behavior tree represents a robot's navigation system with arm activity. The robot must visit the locations "Station A", "Station B", "Station C". 
                  If "Station A" is not reachable, move to "Station D". The only available actions that must be used in the behavior tree are: "MoveTo"."""
example_output = """
<root BTCPP_format="4">
    <BehaviorTree>
        <Sequence>
            <Fallback>
                <MoveTo name="go_to_station_A" location="Station A"/>      <!-- move to Station A -->
                <MoveTo name="go_to_station_D" location="Station D"/>      <!-- move to Station D -->
            </Fallback>
            <MoveTo name="go_to_station_B" location="Station B"/>      <!-- move to Station B -->
            <MoveTo name="go_to_station_C" location="Station C"/>      <!-- move to Station C -->
        </Sequence>
    </BehaviorTree>
</root>
"""

## load base model
base_model.eval()

# Load fine-tuned model
finetuned_model = PeftModel.from_pretrained(base_model, adapter_id, token=hf_token)
finetuned_model = finetuned_model.merge_and_unload()
finetuned_model.eval()

for name in test_file_list:
    print(f"\nRunning inference on task file: {name}")
    task_filename = f"tasks/{name}"

    # load task from the text file
    with open(task_filename, "r") as file:
        task = file.read().strip()

    # zero-shot prompt
    zero_eval_prompt = context + "[INST]" + task + "[/INST]"
    zero_model_input = tokenizer(zero_eval_prompt, return_tensors="pt").to("cuda")

    # one-shot prompt
    one_eval_prompt = context + "[INST]" + example_task + "[/INST]" + example_output + "[INST]" + task + "[/INST]"
    one_model_input = tokenizer(one_eval_prompt, return_tensors="pt").to("cuda")

    ## print task
    print("Task:")
    print(task)

    print("\n zero-shot prompt:")
    print(zero_eval_prompt)

    print("\n one-shot prompt:")
    print(one_eval_prompt)

    for it in range(1, 11): # 10 iterations
        print(f"\nIteration {it} on llamachat:")

        # Evaluate zero-shot with base model
        with torch.no_grad():
            start1 = time.time()
            result = tokenizer.decode(base_model.generate(**zero_model_input, max_new_tokens=1000)[0], skip_special_tokens=True)
            end1 = time.time()
            print(f"\nZero-shot base model result (time: {end1 - start1:.2f} seconds):")
            print("Zero-shot base model result:")
            print(result)
            save_output_to_file("llamachat-base", "zeroshot", task_filename, it, result)

        ## Evaluate one-shot with base model
        with torch.no_grad():
            start2 = time.time()
            result = tokenizer.decode(base_model.generate(**one_model_input, max_new_tokens=1000)[0], skip_special_tokens=True)
            end2 = time.time()
            print(f"\nOne-shot base model result (time: {end2 - start2:.2f} seconds):")
            print("One-shot base model result:")
            print(result)
            save_output_to_file("llamachat-base", "oneshot", task_filename, it, result)

        # Evaluate zero-shot with finetuned model
        with torch.no_grad():
            start3 = time.time()
            result = tokenizer.decode(finetuned_model.generate(**zero_model_input, max_new_tokens=1000)[0], skip_special_tokens=True)
            end3 = time.time()
            print(f"\nZero-shot finetuned model result (time: {end3 - start3:.2f} seconds):")
            print("Zero-shot finetuned model result:")
            print(result)
            save_output_to_file("llamachat-finetuned", "zeroshot", task_filename, it, result)

        # Evaluate oneshot with finetuned model
        with torch.no_grad():
            start4 = time.time()
            result = tokenizer.decode(finetuned_model.generate(**one_model_input, max_new_tokens=1000)[0], skip_special_tokens=True)
            end4 = time.time()
            print(f"\nOne-shot finetuned model result (time: {end4 - start4:.2f} seconds):")
            print("One-shot finetuned model result:")
            print(result)
            save_output_to_file("llamachat-finetuned", "oneshot", task_filename, it, result)