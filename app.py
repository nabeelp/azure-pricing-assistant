"""Flask web application for Azure Pricing Assistant."""

import asyncio
import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework import SequentialBuilder
# from agent_framework.observability import setup_observability

from src.agents import (
    create_question_agent,
    create_bom_agent,
    create_pricing_agent,
    create_proposal_agent,
)

# Load environment variables
load_dotenv()

# Setup observability
# setup_observability()

app = Flask(__name__)
flask_secret_key = os.getenv("FLASK_SECRET_KEY")
if not flask_secret_key:
    raise RuntimeError(
        "FLASK_SECRET_KEY environment variable is not set. "
        "Set this variable to a strong, consistent value for production deployments. "
        "See Flask documentation for details."
    )
app.secret_key = flask_secret_key

# Store active chat threads in memory (in production, use Redis or similar)
chat_threads = {}


async def chat_message(session_id: str, user_message: str):
    """Process a single chat message and return agent response."""
    try:
        credential = DefaultAzureCredential()
        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        async with AzureAIAgentClient(
            project_endpoint=endpoint,
            async_credential=credential
        ) as client:
            # Always create a fresh agent with the current client
            question_agent = create_question_agent(client)

            # Get or create thread
            if session_id not in chat_threads:
                thread = question_agent.get_new_thread()
                chat_threads[session_id] = {
                    'thread': thread,
                    'history': []
                }
            
            session_data = chat_threads[session_id]
            thread = session_data['thread']
            
            # Stream agent response
            response_text = ""
            async for update in question_agent.run_stream(user_message, thread=thread):
                if update.text:
                    response_text += update.text
            
            # Store in history
            session_data['history'].append({
                'role': 'user',
                'content': user_message
            })
            session_data['history'].append({
                'role': 'assistant',
                'content': response_text
            })
            
            # Check if done
            is_done = "We are DONE!" in response_text
            
            return {
                'response': response_text,
                'is_done': is_done,
                'history': session_data['history']
            }
                
    except Exception as e:
        return {
            'error': str(e),
            'response': f"Error: {str(e)}",
            'is_done': False
        }


async def generate_proposal(session_id: str):
    """Generate BOM, pricing, and proposal from requirements."""
    try:
        if session_id not in chat_threads:
            return {'error': 'No active session found'}
        
        session_data = chat_threads[session_id]
        
        # Extract requirements from history
        requirements = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in session_data['history']
        ])
        
        credential = DefaultAzureCredential()
        endpoint = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
        async with AzureAIAgentClient(
            project_endpoint=endpoint,
            async_credential=credential
        ) as client:
            # Create agents
            bom_agent = create_bom_agent(client)
            pricing_agent = create_pricing_agent(client)
            proposal_agent = create_proposal_agent(client)
            
            # Build sequential workflow
            workflow = SequentialBuilder().participants([
                bom_agent,
                pricing_agent,
                proposal_agent
            ]).build()
            
            # Run workflow and collect outputs
            bom_output = ""
            pricing_output = ""
            proposal_output = ""
            current_agent = ""
            
            async for event in workflow.run_stream(requirements):
                # Track agent changes
                if hasattr(event, 'executor_id') and event.executor_id:
                    current_agent = event.executor_id
                
                # Collect outputs
                if hasattr(event, 'data') and event.data:
                    text = None
                    if isinstance(event.data, str):
                        text = event.data
                    elif hasattr(event.data, 'text'):
                        text = event.data.text
                    
                    if text:
                        if current_agent == "bom_agent":
                            bom_output += text
                        elif current_agent == "pricing_agent":
                            pricing_output += text
                        elif current_agent == "proposal_agent":
                            proposal_output += text
            
            return {
                'bom': bom_output,
                'pricing': pricing_output,
                'proposal': proposal_output
            }
                
    except Exception as e:
        return {
            'error': str(e)
        }


@app.route('/')
def index():
    """Render main page."""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages."""
    data = request.json
    session_id = session.get('session_id', os.urandom(16).hex())
    session['session_id'] = session_id
    
    user_message = data.get('message', '')
    
    # Run async chat_message in event loop
    try:
        result = asyncio.run(chat_message(session_id, user_message))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-proposal', methods=['POST'])
def generate():
    """Generate full proposal."""
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    # Run async generate_proposal in event loop
    try:
        result = asyncio.run(generate_proposal(session_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset chat session."""
    session_id = session.get('session_id')
    if session_id and session_id in chat_threads:
        del chat_threads[session_id]
    session.clear()
    return jsonify({'status': 'reset'})


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)
