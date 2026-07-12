from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel
import torch, accelerate
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
model_id = 'codellama/CodeLlama-7b-Instruct-hf'

# Adapters path
adapter_id = 'AIRLab-POLIMI/codellama-7b-instruct-hf-btgenbot-adapter'

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
    token = hf_token,  # Use the token if available
)

# Define the context for the task
context1 =  """<<SYS>>Build a xml plan based on the availbale capabilities to acheive mentioned task of <</SYS>>"""
context2 =  """. Return only the xml plan without explanations or comments. The capabilities of the robot are given as follows, This capability depends on the navigation
             stack functionalities and allow the robot to navigate to a location given by two dimensional coordinates. This capability can be used by the decision making
             authority such as an LLM to move the robot to a required position and orientation. This capability can be triggered via the xml command 
            '<Runner interface=capabilities2_runner_nav2/WaypointRunner provider=capabilities2_runner_nav2/WaypointRunner x='$value' y='$value' />'. '$value' represents a 
             value in meters. As an example '<Runner interface=capabilities2_runner_nav2/WaypointRunner provider=capabilities2_runner_nav2/WaypointRunner x='1.2' y='0.8' /> 
             means the robot will move 1.2 meters forward and 0.8 meters to the right side. All plans need to be contained within 
             <Plan> and </Plan> xml tags. <Control type= name=> </Control> dictates the control flow of the plan and has two attributes, type and name. The type attribute 
             can be one of the following values: sequential, parallel_any, parallel_all, recovery. The name attribute is optional and can be used to give a name to the 
             control flow. '<?xml version='1.0' encoding='UTF-8'?>' should be the first line of the xml file and it is not a part of the plan. Additionally the attribute 
             values should be enclosed within double quotes. The plan can contain multiple control flows and capabilities. Keep the interface and provider attributes of 
             the Runner correctly matched with their namespace and wrong interface and provider values will result in the plan being rejected. 
             <Control type=sequential name=name_of_flow> </Control> will trigger children one after the other depending on predecessor's successful completion 
             <Control type=parallel_any name=name_of_flow> </Control> will trigger children one after another depending on predecessor's successful start up and making it 
             psudo-parallel. All children will execute until at least one capability to finishes before proceeding to execute the rest of the plan. 
             <Control type=parallel_all name=name_of_flow> </Control> will trigger children one after another depending on predecessor's successful start up and making it 
             psudo-parallel. All children will execute until all capabilities finish before proceeding to execute the rest of the plan. 
             <Control type=recovery name=name_of_flow> </Control> will trigger children only on the immediate predecessor's failure. Capabilities within recovery control 
             flow will be executed sequentially on predecessors failure, until at least one capability finishes successfully, and then rest of the recovery capabilities 
             will be skipped and the main plan will continue execution."""

# One-shot example
example_task = """Following example plan shows how to navigate to a series of waypoints, specifically (5.0, 5.0), (2.0,2.0) and (3.0, 1.0) in order. And if the robot 
                cannot reach point (5.0, 5.0) it can move to (0.0, 0.0) as a recovery measure.: """
example_output = """
'<?xml version='1.0' encoding='UTF-8'?>
  <Plan>
      <Control type='sequential' name='main_execution_plan'>
      <Runner interface='capabilities2_runner_nav2/WaypointRunner' provider='capabilities2_runner_nav2/WaypointRunner' x='5.0' y='5.0' />
      <Control type='recovery' name='return_to_home_if_lost'>
          <Runner interface='capabilities2_runner_nav2/WaypointRunner' provider='capabilities2_runner_nav2/WaypointRunner' x='0.0' y='0.0' />
      </Control>
      <Runner interface='capabilities2_runner_nav2/WaypointRunner' provider='capabilities2_runner_nav2/WaypointRunner' x='2.0' y='2.0' />
      <Runner interface='capabilities2_runner_nav2/WaypointRunner' provider='capabilities2_runner_nav2/WaypointRunner' x='3.0' y='1.0' />
      </Control>
  </Plan>'"
"""
## load base model
base_model.eval()

# Load fine-tuned model
finetuned_model = PeftModel.from_pretrained(base_model, adapter_id, token=hf_token)
finetuned_model = finetuned_model.merge_and_unload()
finetuned_model.eval()

# Iterate through each task file
for name in test_file_list:
    print(f"\nRunning inference on task file: {name}")
    task_filename = f"tasks/{name}"

    # load task from the text file
    with open(task_filename, "r") as file:
        task = file.read().strip()

   # zero-shot prompt
    zero_eval_prompt = context1 + "[INST]" + task + context2 + "[/INST]"
    zero_model_input = tokenizer(zero_eval_prompt, return_tensors="pt").to("cuda")

    # one-shot prompt
    one_eval_prompt = context1 + "[INST]" + task + context2 + example_task + "[/INST]" + example_output
    one_model_input = tokenizer(one_eval_prompt, return_tensors="pt").to("cuda")

    ## print task
    print("Task:")
    print(task)

    print("\n zero-shot prompt:")
    print(zero_eval_prompt)

    print("\n one-shot prompt:")
    print(one_eval_prompt)

    for it in range(1, 11): # 10 iterations
        print(f"\nIteration {it}:")

        # Evaluate zero-shot with base model
        with torch.no_grad():
            start1 = time.time()
            result = tokenizer.decode(base_model.generate(**zero_model_input, max_new_tokens=1000)[0], skip_special_tokens=True)
            end1 = time.time()
            print(f"\nZero-shot base model result (time: {end1 - start1:.2f} seconds):")
            print("Zero-shot base model result:")
            print(result)
            save_output_to_file("codellama-base", "zeroshot", task_filename, it, result)

        ## Evaluate one-shot with base model
        with torch.no_grad():
            start2 = time.time()
            result = tokenizer.decode(base_model.generate(**one_model_input, max_new_tokens=1000)[0], skip_special_tokens=True)
            end2 = time.time()
            print(f"\nOne-shot base model result (time: {end2 - start2:.2f} seconds):")
            print("One-shot base model result:")
            print(result)
            save_output_to_file("codellama-base", "oneshot", task_filename, it, result)

        # Evaluate zero-shot with finetuned model
        with torch.no_grad():
            start3 = time.time()
            result = tokenizer.decode(finetuned_model.generate(**zero_model_input, max_new_tokens=1000)[0], skip_special_tokens=True)
            end3 = time.time()
            print(f"\nZero-shot finetuned model result (time: {end3 - start3:.2f} seconds):")
            print("Zero-shot finetuned model result:")
            print(result)
            save_output_to_file("codellama-finetuned", "zeroshot", task_filename, it, result)

        # Evaluate oneshot with finetuned model
        with torch.no_grad():
            start4 = time.time()
            result = tokenizer.decode(finetuned_model.generate(**one_model_input, max_new_tokens=1000)[0], skip_special_tokens=True)
            end4 = time.time()
            print(f"\nOne-shot finetuned model result (time: {end4 - start4:.2f} seconds):")
            print("One-shot finetuned model result:")
            print(result)
            save_output_to_file("codellama-finetuned", "oneshot", task_filename, it, result)