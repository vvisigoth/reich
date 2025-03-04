import os
import time
import argparse
import requests
import json
import sys
import base64
from pathlib import Path
from mimetypes import guess_type
import re
import glob
import subprocess

# Import the diarize module from the current project
import diarize

# Constants
DIALOGUE_DIR = "dialogue/"
PREAMBLE_FILE = "preamble.txt"
EXCLUDE_FILE = "exclude.txt"
GENERATED_DIR = "generated/"
SERVER_URL = "http://localhost:5555/api"  # Default server URL

def get_epoch_time():
    return str(int(time.time()))

def encode_image(image_path):
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'

    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{base64_encoded_data}"

def save_prompt(prompt_text, final_context):
    epoch_time = get_epoch_time()
    prompt_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-prompt.txt")
    context_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-context.txt")
    
    try:
        with open(prompt_file, 'w') as f:
            f.write(prompt_text)

        with open(context_file, 'w') as f:
            f.write(final_context)

    except Exception as e:
        print(f"Error saving files: {e}")
    
    return epoch_time, prompt_file, context_file

def load_preamble():
    with open(PREAMBLE_FILE, 'r') as f:
        return f.read().strip()

def load_exclusions():
    if os.path.exists(EXCLUDE_FILE):
        with open(EXCLUDE_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []

def generate_directory_structure(root_dir, exclude_file):
    exclude_list = []
    if os.path.exists(exclude_file):
        with open(exclude_file, 'r') as f:
            exclude_list = [line.strip() for line in f.readlines()]

    # Construct the tree command with excludes
    exclude_params = []
    for item in exclude_list:
        exclude_params.append(f"-I '{item}'")

    exclude_str = ' '.join(exclude_params)
    command = f"tree {root_dir} {exclude_str} --prune"
    
    # Execute the tree command
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    
    return result.stdout

def gather_context(exclusions):
    # Generate the directory structure
    dir_structure = generate_directory_structure('.', EXCLUDE_FILE)
    context = f"Directory Structure:\n{dir_structure}"
    
    all_files = [f for f in glob.glob("**/*", recursive=True) if os.path.isfile(f)]
    exclude_files = []
    exclude_dirs = []
    for pattern in exclusions:
        if '.' in pattern:
            exclude_files.append(pattern)
        else:
            exclude_dirs.append(pattern)

    # Append contents of files to the context, considering exclusions
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

def send_request_to_server(prompt, encoded_image=None, server_url=SERVER_URL, provider="auto"):
    """Send request to the AI server"""
    # Gather message history
    message_history = gather_message_history()
    
    # Add current prompt to message history
    if encoded_image:
        if provider == "anthropic":
            # Format for Anthropic API
            message_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": guess_image_mime_type(encoded_image),
                            "data": encoded_image.split(",", 1)[1]  # Remove the "data:image/jpeg;base64," prefix
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            })
        else:
            # Format for OpenAI API (default)
            message_history.append({
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": encoded_image
                        }
                    }
                ]
            })
    else:
        message_history.append({"role": "user", "content": prompt})
    
    # Prepare request data
    request_data = {
        "messages": message_history,
        "max_tokens": 1500,
        "temperature": 0.7,
        "provider": provider
    }
    
    # Add model parameter based on provider
    if provider == "anthropic":
        request_data["model"] = "claude-3-5-sonnet-20240620"  # Use a supported model version
    else:
        request_data["model"] = "gpt-4o"
    
    # Send request to server
    try:
        response = requests.post(
            f"{server_url}/generate",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        # Handle response
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                return result.get("content", "")
            else:
                error_msg = result.get("error", "Unknown error")
                raise Exception(f"Server error: {error_msg}")
        else:
            raise Exception(f"HTTP error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Connection error: {str(e)}")

def guess_image_mime_type(encoded_image):
    """Guess the MIME type of the image from the data URL"""
    if encoded_image.startswith("data:image/jpeg"):
        return "image/jpeg"
    elif encoded_image.startswith("data:image/png"):
        return "image/png"
    elif encoded_image.startswith("data:image/gif"):
        return "image/gif"
    elif encoded_image.startswith("data:image/webp"):
        return "image/webp"
    else:
        return "application/octet-stream"  # Default to binary data if unknown
    
def main():
    """Main function to run the Reich client."""
    Path(DIALOGUE_DIR).mkdir(exist_ok=True)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Reich client for AI text generation")
    parser.add_argument('-f', '--file', help='File path to read prompt from')
    parser.add_argument("-i", "--image", required=False, help="Image file to send along with the prompt")
    parser.add_argument("-s", "--server", default=SERVER_URL, help=f"Server URL (default: {SERVER_URL})")
    parser.add_argument("-p", "--provider", default="auto", choices=["auto", "openai", "anthropic"], 
                        help="AI provider to use (default: auto)")
    args = parser.parse_args()
    
    # Process user input
    encoded_image = None
    if args.file:
        with open(os.path.expanduser(args.file), 'r') as file:
            user_prompt = file.read()
    else:
        user_prompt = input("\nEnter your prompt: ")
    
    # Process image if provided
    if args.image:
        encoded_image = encode_image(args.image)
    
    # Load context
    preamble = load_preamble() if os.path.exists(PREAMBLE_FILE) else ""
    exclusions = load_exclusions()
    context = gather_context(exclusions)
    
    # Prepare final prompt with context
    final_prompt = f"{preamble}\n\n{user_prompt}\n\n{context}"
    epoch_time, prompt_file, context_file = save_prompt(user_prompt, final_context=final_prompt)
    
    try:
        # Send request to AI server
        response_text = send_request_to_server(
            prompt=final_prompt, 
            encoded_image=encoded_image,
            server_url=args.server,
            provider=args.provider
        )
        
        # Save the response
        response_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-response.txt")
        with open(response_file, 'w') as f:
            f.write(response_text)
        
        # Extract and save code blocks if present
        code_blocks = re.findall(r'```(.*?)```', response_text, re.DOTALL)
        if code_blocks:
            Path(GENERATED_DIR).mkdir(exist_ok=True)
            for i, code_block in enumerate(code_blocks):
                code_block = code_block.strip()
                if code_block.startswith('python'):
                    extension = '.py'
                    content = code_block.split('\n', 1)[1] if '\n' in code_block else code_block
                elif code_block.startswith('javascript'):
                    extension = '.js'
                    content = code_block.split('\n', 1)[1] if '\n' in code_block else code_block
                else:
                    extension = '.txt'
                    content = code_block
                    
                filename = os.path.join(GENERATED_DIR, f"{epoch_time}_{i}{extension}")
                with open(filename, 'w') as file:
                    file.write(content)
        
        # Print the response
        print("\n" + "="*50)
        print("RESPONSE:")
        print("="*50)
        print(response_text)
        
        # Update conversation summary
        if 'diarize' in sys.modules:
            diarize.summarize_conversation()
            
    except Exception as e:
        print(f"Error in processing: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
