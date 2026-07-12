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