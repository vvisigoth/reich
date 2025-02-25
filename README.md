# Reich

**NOTE** AI generated Readme based on ongoing work. Generated not read.

## Overview

This project provides an AI-based code assistant that interacts with users to process prompts, summarize conversations, and manage dialogue history. It leverages OpenAI's API to interpret user inputs, generate responses, and summarize previous interactions. Each project is managed in its own directory structure, allowing for isolated and independent handling of dialogues and generated content.

## Directory Structure

```
.
├── diarize.py
├── key
├── preamble.txt
├── pyvenv.cfg
├── reich.py
├── summarize_new.py
├── system.txt
└── tokencheck.py
```

### File Descriptions

- **diarize.py**: Handles the summarization of conversations by processing dialogue files and generating concise summaries using OpenAI's API.
  
- **key**: Contains the API key necessary for authenticating requests to OpenAI's services. **Ensure this file is kept secure and private.**

- **preamble.txt**: A text file containing the initial context or preamble that is included in every prompt sent to the AI.

- **pyvenv.cfg**: Configuration file for the Python virtual environment, specifying the Python version and environment settings.

- **reich.py**: The main script that coordinates the interaction with users, manages dialogue and context, and handles the process of sending prompts and receiving responses from the AI.

- **summarize_new.py**: A module similar to `diarize.py`, focused on summarizing conversations but with updated or experimental features.

- **system.txt**: Defines the role and behavior of the AI system, guiding it to respond appropriately to various requests related to coding tasks.

- **tokencheck.py**: A utility script for estimating the number of tokens in a given text, based on the specified language model.

## Setup and Installation

1. **Python Environment**: Ensure you have Python 3.9.6 installed. You can check and set up a virtual environment using the provided `pyvenv.cfg`.

2. **Dependencies**: Install necessary Python packages by running:
   ```bash
   pip install openai tiktoken
   ```

3. **API Key**: Place your OpenAI API key in the `key` file. Ensure that this file is kept private and not shared publicly.

4. **Directory Setup**: Ensure each project you work with has its own set of directories (`dialogue/`, `generated/`, etc.) to keep them separate and organized.

## Usage

- **Running reich.py**: This is the main script for interaction. You can run it using:
  ```bash
  python reich.py -f [prompt-file] -i [image-file]
  ```
  - `-f`: Specifies a file containing the prompt to be sent.
  - `-i`: Optionally specifies an image to be sent with the prompt.

- **Token Estimation**: Use `tokencheck.py` to estimate the number of tokens in a text file:
  ```bash
  python tokencheck.py -f [text-file]
  ```

- **Summarization**: `diarize.py` and `summarize_new.py` are used to generate summaries of dialogues. You can run these scripts directly to process and summarize existing dialogue files.

## Features

- **Dynamic Context Handling**: Combines user prompts with a preamble and relevant project context to generate comprehensive inputs for the AI.

- **Conversation Summarization**: Automatically summarizes dialogue exchanges after a set number of interactions, maintaining concise historical context.

- **Token Management**: Provides functionality to estimate the token count of a given text, aiding in managing API input constraints.

## Security and Privacy

- **API Key**: The API key is sensitive information and should be stored securely. Avoid including it in version control systems.

- **Data Handling**: Ensure that all dialogue and generated content is stored securely, especially if it involves sensitive or proprietary information.

## Contributions

Contributions are welcome! Please ensure that any changes maintain the modular structure and do not compromise the security of the API key or user data.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.

---

Feel free to customize the README further to fit the specific details and goals of your project.
# TODO

- insert tree for repo context
- Git integration
- Summarize code to make searching easier
- Regression tests
- Unit tests
- Precheck tokens

