import os
import time
import argparse
from PIL import Image
import io
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
# import utility to 
from url_fetch import capture_webpage

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

def process_image(image_path, max_height=7999):
    with Image.open(image_path) as img:
        width, height = img.size
        
        # Check if image needs to be split
        if height > width * 4/3 and height > max_height:
            pieces = []
            for i in range(0, height, max_height):
                box = (0, i, width, min(i+max_height, height))
                piece = img.crop(box)
                
                # Convert piece to base64
                buffer = io.BytesIO()
                piece.save(buffer, format="PNG")
                encoded_piece = base64.b64encode(buffer.getvalue()).decode('utf-8')
                pieces.append(f"data:image/png;base64,{encoded_piece}")
            
            return pieces
        else:
            # If image doesn't need splitting, return it as is
            return [encode_image(image_path)]

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

def send_request_to_server(prompt, image_paths=None, server_url=SERVER_URL, provider="openrouter", model="claude-3-7-sonnet-20250219"):
    message_history = gather_message_history()

    print("message_history", message_history)
    
    if image_paths:
        for image_path in image_paths:
            image_pieces = process_image(image_path)
            for piece in image_pieces:
                if provider == "anthropic":
                    message_history.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": piece.split(",", 1)[1]
                                }
                            }
                        ]
                    })
                else:
                    message_history.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": piece
                                }
                            }
                        ]
                    })
    
    # Add the text prompt last
    message_history.append({"role": "user", "content": prompt})

    # Prepare request data
    request_data = {
        "messages": message_history,
        "max_tokens": 1500,
        "temperature": 0.7,
        "provider": provider,
        "model": model
    }
    
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
    parser.add_argument('-f', '--file', default='prompt', help='File path to read prompt from')
    parser.add_argument("-i", "--images", nargs='+', required=False, help="Image files to send along with the prompt")
    parser.add_argument("-u", "--urls", nargs='+', required=False, help="URLs to capture screenshots from")
    parser.add_argument("-s", "--server", default=SERVER_URL, help=f"Server URL (default: {SERVER_URL})")
    parser.add_argument("-p", "--provider", default="openrouter", choices=["auto", "openai", "openrouter", "anthropic"])
    parser.add_argument("-m", "--model", default="anthropic/claude-3.7-sonnet", help="Model to use")

    args = parser.parse_args()
    
    # Process user input
    if args.file:
        with open(os.path.expanduser(args.file), 'r') as file:
            user_prompt = file.read()
    else:
        user_prompt = input("\nEnter your prompt: ")
    
    # Capture screenshots if URLs are provided
    captured_images = []
    if args.urls:
        for url in args.urls:
            screenshot_path = capture_webpage(url)
            captured_images.append(screenshot_path)
    
    # Combine captured screenshots with provided images
    image_paths = (args.images or []) + captured_images
    
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
            image_paths=image_paths,
            server_url=args.server,
            provider=args.provider,
            model=args.model
        )
        
        # Parse and save response components (JSON format if available)
        response_file, processed_response = save_response_components(epoch_time, response_text)
        
        # Extract and save code blocks if present
        code_blocks = re.findall(r'```(.*?)```', processed_response, re.DOTALL)
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
        print(processed_response)
        
        # Print information about any patches or commands
        is_json, text, patch, commands = parse_json_response(response_text)
        if is_json:
            if patch:
                patch_file = os.path.join("patches", f"{epoch_time}-patch.txt")
                print(f"\nPatch file saved to: {patch_file}")
                print("To apply the patch, run:")
                print(f"  git apply {patch_file}")
            
            if commands:
                print("\nCommands generated:")
                for i, cmd in enumerate(commands):
                    cmd_file = os.path.join("commands", f"{epoch_time}-cmd{i+1}.sh")
                    print(f"  [{i+1}] {cmd} (saved to {cmd_file})")
                print("\nTo run a command, execute:")
                print(f"  bash commands/{epoch_time}-cmd#.sh")
        
        # Update conversation summary
        #jif 'diarize' in sys.modules:
        #j    diarize.summarize_conversation()
            
    except Exception as e:
        print(f"Error in processing: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())
