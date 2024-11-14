import os
import time
import argparse
from openai import OpenAI
import base64
import glob
from pathlib import Path
from mimetypes import guess_type
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DIALOGUE_DIR = "dialogue/"
PREAMBLE_FILE = "preamble.txt"
EXCLUDE_FILE = "exclude.txt"
GENERATED_DIR = "generated/"

def get_epoch_time():
    return str(int(time.time()))

def encode_image(image_path):
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'

    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{base64_encoded_data}"

def save_prompt(prompt_text):
    epoch_time = get_epoch_time()
    prompt_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-prompt.txt")
    with open(prompt_file, 'w') as f:
        f.write(prompt_text)
    return epoch_time, prompt_file

def load_preamble():
    with open(PREAMBLE_FILE, 'r') as f:
        return f.read().strip()

def load_exclusions():
    if os.path.exists(EXCLUDE_FILE):
        with open(EXCLUDE_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []

def gather_context(exclusions):
    context = ""
    all_files = [f for f in glob.glob("**/*", recursive=True) if os.path.isfile(f)]
    exclude_files = []
    exclude_dirs = []
    for pattern in exclusions:
        if '.' in pattern:
            exclude_files.append(pattern)
        else:
            exclude_dirs.append(pattern)
    for file in all_files:
        if any(file.startswith(excluded_dir) for excluded_dir in exclude_dirs):
            continue
        if any(glob.fnmatch.fnmatch(file, pattern) for pattern in exclude_files):
            continue
        with open(file, 'r', errors="ignore") as f:
            context += f"\n\n# Content of {file}:\n"
            context += f.read()
    return context

def gather_message_history():
    files = sorted(glob.glob(os.path.join(DIALOGUE_DIR, "*.txt")), key=os.path.getmtime)
    summaries = [f for f in files if "summary" in f]
    prompts = [f for f in files if "prompt" in f]
    responses = [f for f in files if "response" in f]

    message_history = []

    if summaries:
        with open(summaries[-1], 'r') as f:
            message_history.append({"role": "assistant", "content": f.read().strip()})

    for p, r in zip(prompts, responses):
        with open(p, 'r') as f:
            message_history.append({"role": "user", "content": f.read().strip()})
        with open(r, 'r') as f:
            message_history.append({"role": "assistant", "content": f.read().strip()})

    return message_history

def send_prompt_to_openai(prompt, encoded_image):
    message_history = gather_message_history()
    if encoded_image:
        message_history.append(
            {"role": "user", "content":
                [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url", "image_url":
                            {
                                "url": encoded_image
                            }
                    }
                ]
            })
    else:
        message_history.append({"role": "user", "content": prompt})
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=message_history,
        max_tokens=1500,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def save_response(epoch_time, response_text):
    response_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-response.txt")
    with open(response_file, 'w') as f:
        f.write(response_text)
    return response_file

def extract_code_blocks(text):
    code_blocks = re.findall(r'```(.*?)```', text, re.DOTALL)
    return code_blocks

def save_code_blocks(code_blocks):
    Path(GENERATED_DIR).mkdir(exist_ok=True)
    for i, code_block in enumerate(code_blocks):
        code_block = code_block.strip()
        if code_block.startswith('python'):
            extension = '.py'
        elif code_block.startswith('javascript'):
            extension = '.js'
        elif code_block.startswith('java'):
            extension = '.java'
        else:
            extension = '.txt'
        filename = os.path.join(GENERATED_DIR, f"{get_epoch_time()}_{i}{extension}")
        with open(filename, 'w') as file:
            if extension in ['.py', '.js', '.java']:
                file.write(code_block.split('\n', 1)[1])
            else:
                file.write(code_block)

def print_history():
    files = sorted(glob.glob(os.path.join(DIALOGUE_DIR, "*.txt")), key=os.path.getmtime)
    for file in files:
        with open(file, 'r') as f:
            print(f"\n{'-'*50}\n# Content of {file}:\n{'-'*50}")
            print(f.read())

def main():
    Path(DIALOGUE_DIR).mkdir(exist_ok=True)
    while True:
        print_history()
        parser = argparse.ArgumentParser()
        parser.add_argument('-f', '--file', help='File path to read prompt from')
        parser.add_argument("-i", "--image", required=False, help="Image file to send along with the prompt.")
        args = parser.parse_args()
        encoded_image = None

        if args.file:
            with open(os.path.expanduser(args.file), 'r') as file:
                user_prompt = file.read()
            if args.image:
                encoded_image = encode_image(args.image)
        else:
            user_prompt = input("\nEnter your prompt: ")

        epoch_time, prompt_file = save_prompt(user_prompt)
        preamble = load_preamble()
        exclusions = load_exclusions()
        context = gather_context(exclusions)
        final_prompt = f"{preamble}\n\n{user_prompt}\n\n{context}"
        response = send_prompt_to_openai(final_prompt, encoded_image)
        response_file = save_response(epoch_time, response)

        # Extract code blocks and save them
        code_blocks = extract_code_blocks(response)
        save_code_blocks(code_blocks)

if __name__ == "__main__":
    main()
