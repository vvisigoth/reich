# Reich - AI Assistant CLI Tool

Reich is a command-line interface tool for interacting with large language models (LLMs), currently supporting both OpenAI's GPT models and Anthropic's Claude models. It allows you to send prompts, include context from your current directory, and save the conversation history.

## Features

- Send prompts to OpenAI GPT models or Anthropic Claude models
- Include images with your prompts (OpenAI only)
- Automatically include directory structure and file contents as context
- Save conversation history for future reference
- Extract and save code blocks from responses
- Summarize conversations for better context management

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/reich.git
   cd reich
   ```

2. Install the required packages:
   ```
   pip install openai anthropic
   ```

3. Set up your configuration:
   ```
   cp example.config.json config.json
   ```

4. Edit `config.json` to include your API keys:
   ```json
   {
     "openai_api_key": "your-openai-api-key",
     "anthropic_api_key": "your-anthropic-api-key"
   }
   ```

   Note: If both API keys are provided, Reich will default to using OpenAI. If only one API key is provided, it will use the available service.

## Usage

### Basic Usage

To start a basic conversation:

```
python reich.py
```

You'll be prompted to enter your query.

### Reading Prompts from a File

To read a prompt from a file:

```
python reich.py -f path/to/prompt.txt
```

### Including an Image (OpenAI only)

To include an image with your prompt:

```
python reich.py -i path/to/image.jpg
```

Or combined with a file prompt:

```
python reich.py -f path/to/prompt.txt -i path/to/image.jpg
```

## Configuration Files

- `config.json`: Contains your API keys for OpenAI and Anthropic
- `preamble.txt`: Contains system instructions that are sent with each prompt
- `exclude.txt`: List of files or directories to exclude from context

## Directory Structure

```
.
├── backup.py              # Backup script
├── config.example.json    # Example configuration
├── config.json            # Your configuration (with API keys)
├── dialogue/              # Directory where conversation history is stored
├── example.config.json    # Another example configuration format
├── exclude.txt            # Files/directories to exclude from context
├── generated/             # Directory where extracted code is saved
├── preamble.txt           # System instructions for the AI
├── reich.py               # Main script
└── system.txt             # Additional system context
```

## How It Works

1. When you run `reich.py`, it gathers context from your current directory
2. It combines your prompt with a preamble and the gathered context
3. It sends this to either OpenAI's GPT or Anthropic's Claude API depending on your configuration
4. The response is saved to the `dialogue` directory
5. Any code blocks in the response are extracted and saved to the `generated` directory
6. The conversation is summarized for future context

## License

[TBD]
