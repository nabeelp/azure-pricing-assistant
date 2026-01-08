"""Flask web application for Azure Pricing Assistant."""

import asyncio
import json
import os
import logging
from flask import Flask, render_template, request, jsonify, session, Response

from src.core.config import get_flask_secret, load_environment
from src.core.session import InMemorySessionStore
from src.shared.async_utils import run_coroutine
from src.shared.logging import setup_logging
from src.web.interface import WebInterface
from src.web.handlers import WebHandlers

# Load environment and configure Flask
load_environment()

# Resolve desired log level from environment (default INFO)
_level_name = os.getenv("APP_LOG_LEVEL", "INFO").upper()
_level = getattr(logging, _level_name, logging.INFO)

# Configure logging with selected level
setup_logging(
    name="pricing_assistant_web",
    level=_level,
    service_name="azure-pricing-assistant-web",
)

# Quiet noisy third-party loggers (access logs, SDKs, telemetry)
for _noisy in ("werkzeug", "opentelemetry", "azure", "agent_framework"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# Resolve template directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)
app.secret_key = get_flask_secret()

# Initialize shared components
session_store = InMemorySessionStore()
web_interface = WebInterface(session_store)
handlers = WebHandlers(web_interface)


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
    
    # Run async handler in event loop
    try:
        result = run_coroutine(handlers.handle_chat(session_id, user_message))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-proposal', methods=['POST'])
def generate():
    """Generate full proposal."""
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    # Run async handler in event loop
    try:
        result = run_coroutine(handlers.handle_generate_proposal(session_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-proposal-stream', methods=['GET'])
def generate_stream():
    """Generate proposal with streaming progress (SSE)."""
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    def event_generator():
        """Bridge async generator to sync generator for Flask."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            async_gen = handlers.handle_generate_proposal_stream(session_id)
            
            while True:
                try:
                    event = loop.run_until_complete(async_gen.__anext__())
                    # Format as SSE
                    yield f"data: {json.dumps(event)}\n\n"
                except StopAsyncIteration:
                    break
        finally:
            loop.close()
    
    return Response(event_generator(), mimetype='text/event-stream')


@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset chat session."""
    session_id = session.get('session_id')
    if session_id:
        run_coroutine(handlers.handle_reset(session_id))
    session.clear()
    return jsonify({'status': 'reset'})


@app.route('/api/history', methods=['GET'])
def history():
    """Get chat history for current session."""
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session', 'history': []}), 400
    
    try:
        result = run_coroutine(handlers.handle_history(session_id))
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'history': []}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    from src.core.config import get_port

    app.run(host='0.0.0.0', port=get_port(), debug=False)
