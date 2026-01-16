"""Flask web application for Azure Pricing Assistant."""

import asyncio
import json
import logging
import os

from flask import Flask, Response, jsonify, render_template, request, session

from opentelemetry import trace
from src.core.config import get_flask_secret, load_environment
from src.core.session import InMemorySessionStore
from src.shared.async_utils import run_coroutine
from src.shared.logging import setup_logging
from src.shared.tracing import configure_tracing
from src.shared.metrics import configure_metrics
from src.web.interface import WebInterface
from src.web.handlers import WebHandlers
from src.web.session_tracing import end_session_span, get_or_create_session_span

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

# Configure OpenTelemetry traces (OTLP/gRPC) and enable Agent Framework spans.
configure_tracing(service_name="azure-pricing-assistant-web")

# Configure OpenTelemetry metrics (OTLP/gRPC)
configure_metrics()

# Resolve template and static directories
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, template_folder=TEMPLATES_DIR, static_folder=STATIC_DIR)
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

    session_span = get_or_create_session_span(session_id)
    with trace.use_span(session_span, end_on_exit=False):
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
    
    session_span = get_or_create_session_span(session_id)
    with trace.use_span(session_span, end_on_exit=False):
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
        session_span = get_or_create_session_span(session_id)
        with trace.use_span(session_span, end_on_exit=False):
            yield from _run_stream_generator(session_id)

    def _run_stream_generator(session_id: str):
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
        except Exception as e:
            # Best-effort error reporting over SSE.
            yield f"data: {json.dumps({'event_type': 'error', 'message': str(e)})}\n\n"
        finally:
            loop.close()
    
    return Response(event_generator(), mimetype='text/event-stream')


@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset chat session."""
    session_id = session.get('session_id')
    try:
        if session_id:
            session_span = get_or_create_session_span(session_id)
            with trace.use_span(session_span, end_on_exit=False):
                run_coroutine(handlers.handle_reset(session_id))
            end_session_span(session_id)
        session.clear()
        return jsonify({'status': 'reset'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/history', methods=['GET'])
def history():
    """Get chat history for current session."""
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session', 'history': []}), 400
    
    session_span = get_or_create_session_span(session_id)
    with trace.use_span(session_span, end_on_exit=False):
        try:
            result = run_coroutine(handlers.handle_history(session_id))
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e), 'history': []}), 500


@app.route('/api/bom', methods=['GET'])
def get_bom():
    """Get current BOM items for the session with caching headers."""
    session_id = session.get('session_id')
    
    # Return empty BOM if no session exists yet (before first message)
    if not session_id:
        return jsonify({
            'bom_items': [],
            'bom_task_status': 'idle',
            'bom_last_update': None,
            'bom_task_error': None
        })
    
    session_span = get_or_create_session_span(session_id)
    with trace.use_span(session_span, end_on_exit=False):
        try:
            result = run_coroutine(handlers.handle_get_bom(session_id))
            
            # Generate ETag from bom_last_update timestamp
            etag = None
            if result.get('bom_last_update'):
                etag = f'"{hash(result["bom_last_update"])}"'
            
            # Check If-None-Match header for ETag-based caching
            if etag and request.headers.get('If-None-Match') == etag:
                return '', 304  # Not Modified
            
            response = jsonify(result)
            
            # Add caching headers
            if etag:
                response.headers['ETag'] = etag
            if result.get('bom_last_update'):
                response.headers['Last-Modified'] = result['bom_last_update']
            
            # Add Cache-Control to allow conditional requests
            response.headers['Cache-Control'] = 'no-cache'
            
            return response
        except Exception as e:
            return jsonify({'error': str(e), 'bom_items': []}), 500


@app.route('/api/proposal', methods=['GET'])
def get_proposal():
    """Get stored proposal for the session."""
    session_id = session.get('session_id')
    
    if not session_id:
        return jsonify({'error': 'No active session'}), 400
    
    session_span = get_or_create_session_span(session_id)
    with trace.use_span(session_span, end_on_exit=False):
        try:
            result = handlers.handle_get_proposal(session_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@app.route('/api/proposals', methods=['GET'])
def get_all_proposals():
    """Get all stored proposals across all sessions."""
    try:
        result = handlers.handle_get_all_proposals()
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'proposals': [], 'count': 0}), 500


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    from src.core.config import get_port

    app.run(host='0.0.0.0', port=get_port(), debug=False)
