import os
import json
import time
import base64
from typing import Dict, Any, Optional, List
from flask import Flask, request, jsonify
from openai import OpenAI
from anthropic import Anthropic

app = Flask(__name__)

# Load Configuration
def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()
openai_api_key = config.get("openai_api_key")
anthropic_api_key = config.get("anthropic_api_key")
openrouter_api_key = config.get("openrouter_api_key")

# Initialize Clients
openai_client = None
anthropic_client = None
openrouter_client = None

if openai_api_key:
    openai_client = OpenAI(api_key=openai_api_key)

if anthropic_api_key:
    anthropic_client = Anthropic(api_key=anthropic_api_key)

if openrouter_api_key:
    openrouter_client = OpenAI(base_url="https://openrouter.ai/api/v1",api_key=openrouter_api_key)

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    model = data.get('model', 'gpt-4o')
    messages = data.get('messages', [])
    max_tokens = data.get('max_tokens', 4000)
    temperature = data.get('temperature', 0.7)
    provider = data.get('provider', 'openrouter')  # Default to OpenAI if not specified
    
    try:
        if provider == 'openai' and openai_client:
            response = openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return jsonify({
                'success': True,
                'content': response.choices[0].message.content.strip(),
                'model': model,
                'provider': 'openai'
            })
            
        elif provider == 'anthropic' and anthropic_client:
            # Convert OpenAI message format to Anthropic format
            anthropic_messages = []
            for msg in messages:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            response = anthropic_client.messages.create(
                model="claude-3-7-sonnet-20250219" if model == "default" else model,
                max_tokens=max_tokens,
                messages=anthropic_messages
            )
            
            return jsonify({
                'success': True,
                'content': response.content[0].text.strip(),
                'model': model,
                'provider': 'anthropic'
            })
        elif provider == 'openrouter' and openrouter_client:
            response = openrouter_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return jsonify({
                'success': True,
                'content': response.choices[0].message.content.strip(),
                'model': model,
                'provider': 'openrouter'
            })
        else:
            return jsonify({
                'success': False,
                'error': f"Provider '{provider}' not available or no valid API keys found."
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    available_providers = []
    if openai_client:
        available_providers.append('openai')
    if anthropic_client:
        available_providers.append('anthropic')
    if anthropic_client:
        available_providers.append('openrouter')
        
    return jsonify({
        'status': 'ok',
        'available_providers': available_providers
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5555))
    app.run(host='0.0.0.0', port=port, debug=True)
