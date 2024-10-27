import os
import time
from openai import OpenAI
import glob
from pathlib import Path
import re

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DIALOGUE_DIR = "dialogue/"
PREAMBLE_FILE = "preamble.txt"
EXCLUDE_FILE = "exclude.txt"
GENERATED_DIR = "generated/"

def get_epoch_time():
    return str(int(time.time()))

def save_prompt(prompt_text):
    epoch_time = get_epoch_time()
    prompt_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-prompt.txt")
    with open(prompt_file, 'w') as f:
        f.write(prompt_text)
    return epoch_time, prompt_file

def load_preamble():
    if os.path.exists(PREAMBLE_FILE):
        with open(PREAMBLE_FILE, 'r') as f:
            return f.read().strip()
    return ""

def load_exclusions():
    if os.path.exists(EXCLUDE_FILE):
        with open(EXCLUDE_FILE, 'r') as f:
            patterns = [line.strip() for line in f if line.strip()]
        return patterns
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

def send_prompt_to_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-4", 
        messages=[
            {"role": "system", "content": "You are an AI code assistant."},
            {"role": "user", "content": prompt}
          ],
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

def identify_language(code_block):
    if code_block.startswith('python'):
        return '.py'
    elif code_block.startswith('javascript'):
        return '.js'
    elif code_block.startswith('java'):
        return '.java'
    # Add more language detections as required
    return '.txt'  # Default extension

def save_code_blocks(code_blocks):
    Path(GENERATED_DIR).mkdir(exist_ok=True)
    for i, code_block in enumerate(code_blocks):
        code_block = code_block.strip()
        extension = identify_language(code_block)
        filename = f"{get_epoch_time()}_{i}{extension}"
        filepath = os.path.join(GENERATED_DIR, filename)
        with open(filepath, 'w') as file:
            # Skip the first line if it's just the language declaration
            lines = code_block.split('\n')
            if len(lines) > 1 and lines[0] in ['python', 'javascript', 'java']:
                file.write('\n'.join(lines[1:]))
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
        user_prompt = input("\nEnter your prompt: ")
        epoch_time, prompt_file = save_prompt(user_prompt)
        preamble = load_preamble()
        exclusions = load_exclusions()
        context = gather_context(exclusions)
        final_prompt = f"{preamble}\n\n{user_prompt}\n\n{context}"
        response = send_prompt_to_openai(final_prompt)
        response_file = save_response(epoch_time, response)

        # Extract code blocks and save them
        code_blocks = extract_code_blocks(response)
        save_code_blocks(code_blocks)

if __name__ == "__main__":
    main()
