import os, re
import time
from openai import OpenAI
from pathlib import Path
import glob
import shutil

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DIALOGUE_DIR = "dialogue/"
HISTORY_DIR = "history/"

def get_epoch_time():
    return str(int(time.time()))

def extract_digits_from_filename(filename):
    match = re.match(r'dialogue/(\d+)-prompt.txt', filename)
    if match:
        return match.group(1)
    return None

def send_summary_request_to_openai(text):
    response = client.chat.completions.create(
        model="gpt-4", 
        messages=[
            {"role": "system", "content": "You are making a concise summary of a conversation between a user an an AI code assistant. 500 words max."},
            {"role": "user", "content": f"Summarize the following exchange: {text}"}
          ],
        max_tokens=1500,
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

def save_summary(summary_text):
    epoch_time = get_epoch_time()
    summary_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-summary.txt")
    with open(summary_file, 'w') as f:
        f.write(summary_text)
    return summary_file

def move_files_to_history(files):
    Path(HISTORY_DIR).mkdir(exist_ok=True)
    for f in files:
        shutil.move(f, HISTORY_DIR)

def watch_dialogue_directory():
    while True:
        files = sorted(glob.glob(os.path.join(DIALOGUE_DIR, "*.txt")), key=os.path.getmtime)
        prompts = [f for f in files if "prompt" in f]
        responses = [f for f in files if "response" in f]
        # This should queue off of responses, as there is a lag between prompts and responses
        if len(responses) > 5:
            text = ""
            for i in range(len(responses)):
                key = extract_digits_from_filename(prompts[i])
                p = prompts[i]
                print(f"prompts: {p}")
                print(f"key {key}")
                with open(prompts[i], 'r') as f:
                    text += "\nUser: " + f.read()
                try:
                    with open(f"dialogue/{key}-response.txt", 'r') as f:
                        text += "\nAI: " + f.read()
                except:
                    text += "\nAI: <no response>"
            summary = send_summary_request_to_openai(text)
            save_summary(summary)
            # Move processed files to history directory
            move_files_to_history(prompts[:5])
            move_files_to_history(responses[:5])
        else:
            time.sleep(1)

def main():
    Path(DIALOGUE_DIR).mkdir(exist_ok=True)
    watch_dialogue_directory()

if __name__ == "__main__":
    main()
