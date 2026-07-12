# Set up the OpenAI client (requires OPENAI_API_KEY in your environment)
from openai import OpenAI
import sys
from file_save import save_output_to_file
import time

client = OpenAI()
MODEL = "gpt-5"  # You can switch to "gpt-4.1" or "o4-mini" if you have access

# List of test files from tasks folder
test_file_list = [
    "generative_1.txt",
    "generative_2.txt",
    "generative_3.txt",
    "generative_4.txt",
    "generative_5.txt",
]

# Define the context for the task
context1 =  """Build a xml plan based on the availbale capabilities to acheive mentioned task of """
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

def generate_bt_with_openai(context: str, task: str, example_task: str | None = None, example_output: str | None = None, model: str = MODEL) -> str:
    """Generate a behavior tree XML using the OpenAI Responses API.

    Returns the raw text response (we'll regex out the <root>...</root> block next).
    """
    messages = []
    if context and context.strip():
        messages.append({ "role": "system", "content": context.strip() })

    # One-shot example, if provided
    if example_task and example_output:
        messages.append({ "role": "user", "content": example_task.strip() })
        messages.append({ "role": "assistant", "content": example_output.strip() })

    messages.append({ "role": "user", "content": task.strip() })

    # Use the Responses API for text output
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=1,
    )
    print("Prompt used: ")
    print(messages)

    return resp.choices[0].message.content

for name in test_file_list:
    print(f"\nRunning inference on task file: {name}")
    task_filename = f"tasks/{name}"

    # load task from the text file
    with open(task_filename, "r") as file:
        task = file.read().strip()
        context = context1 + task + context2

    for it in range(1, 11): # 10 iterations
        print(f"\nIteration {it} on openai-{MODEL}:")

        ## print task
        print("Task:")
        print(task)

        # Generate the behavior tree XML using OpenAI using the zero-shot approach
        start1 = time.time()
        result = generate_bt_with_openai(context, task)
        end1 = time.time()
        print(f"\nZero-shot OpenAI result (time: {end1 - start1:.2f} seconds):")
        print("Zero-shot OpenAI result:")
        print(result)
        save_output_to_file(f"openai-{MODEL}", "zeroshot", task_filename, it, result)

        # Generate the behavior tree XML using OpenAI using the one-shot approach
        start2 = time.time()
        result = generate_bt_with_openai(context, task, example_task, example_output)
        end2 = time.time()
        print(f"\nOne-shot OpenAI result (time: {end2 - start2:.2f} seconds):")
        print("One-shot OpenAI result:")
        print(result)
        save_output_to_file(f"openai-{MODEL}", "oneshot", task_filename, it, result)