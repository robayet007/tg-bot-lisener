"""
Flask API Server for Telegram Bot
Provides endpoints to send messages to the bot and receive responses.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import asyncio
import threading
import time
from datetime import datetime
from telegram_listener import TelegramBotListener
import config

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global bot listener instance
bot_listener = None
listener_thread = None
listener_loop = None


def run_listener():
    """Run the bot listener in a separate thread."""
    global listener_loop
    listener_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(listener_loop)
    
    async def start_listener():
        global bot_listener
        bot_listener = TelegramBotListener()
        await bot_listener.run()
    
    listener_loop.run_until_complete(start_listener())


def start_listener_thread():
    """Start the bot listener in a background thread."""
    global listener_thread
    listener_thread = threading.Thread(target=run_listener, daemon=True)
    listener_thread.start()
    
    # Wait a bit for listener to initialize
    time.sleep(3)
    print("Bot listener started in background thread")


@app.route('/api/send', methods=['GET', 'POST'])
def send_command():
    """Send a command to the bot.
    
    GET: /api/send?command=Krate
    POST: {"command": "Krate"}
    """
    try:
        # Get command from request
        if request.method == 'GET':
            command = request.args.get('command')
        else:
            data = request.get_json() or {}
            command = data.get('command')
        
        if not command:
            return jsonify({
                "success": False,
                "error": "Command parameter is required"
            }), 400
        
        if not bot_listener or not bot_listener.bot_entity:
            return jsonify({
                "success": False,
                "error": "Bot listener not initialized. Please wait a moment and try again."
            }), 503
        
        # Send message to bot
        async def send_and_wait():
            sent_message = await bot_listener.client.send_message(
                bot_listener.bot_entity, 
                command
            )
            
            # Wait for response (max 10 seconds)
            start_time = time.time()
            response = None
            
            while time.time() - start_time < 10:
                await asyncio.sleep(0.5)
                # Check recent responses
                async with bot_listener.response_lock:
                    # Find the most recent response after our message
                    if bot_listener.recent_responses:
                        latest_response = max(
                            bot_listener.recent_responses.values(),
                            key=lambda x: x["date"]
                        )
                        # Check if this response came after our message
                        if latest_response["message_id"] > sent_message.id:
                            response = latest_response
                            break
                
            return {
                "sent_message_id": sent_message.id,
                "response": response
            }
        
        # Run async function
        if listener_loop and listener_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(send_and_wait(), listener_loop)
            result = future.result(timeout=15)
        else:
            return jsonify({
                "success": False,
                "error": "Listener loop not running"
            }), 503
        
        return jsonify({
            "success": True,
            "command": command,
            "sent_message_id": result["sent_message_id"],
            "response": result["response"]
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/api/send-message-raw', methods=['GET', 'POST'])
def send_message_raw():
    """Send a raw message to the bot.
    
    GET: /api/send-message-raw?prefix=ktp&uid=123&diamonds=100
    POST: {"prefix": "ktp", "uid": "uid", "diamonds": "diamonds"}
    """
    try:
        # Get parameters from request
        if request.method == 'GET':
            prefix = request.args.get('prefix')
            uid = request.args.get('uid')
            diamonds = request.args.get('diamonds')
        else:
            data = request.get_json() or {}
            prefix = data.get('prefix')
            uid = data.get('uid')
            diamonds = data.get('diamonds')
        
        if not prefix or not uid or not diamonds:
            return jsonify({
                "success": False,
                "error": "prefix, uid, and diamonds parameters are required"
            }), 400
        
        # Format message: {prefix} {uid} {diamonds}
        message = f"{prefix} {uid} {diamonds}"
        
        if not bot_listener or not bot_listener.bot_entity:
            return jsonify({
                "success": False,
                "error": "Bot listener not initialized. Please wait a moment and try again."
            }), 503
        
        # Send message to bot
        async def send_and_wait():
            sent_message = await bot_listener.client.send_message(
                bot_listener.bot_entity, 
                message
            )
            
            # Wait for response (max 10 seconds)
            start_time = time.time()
            response = None
            
            while time.time() - start_time < 10:
                await asyncio.sleep(0.5)
                # Check recent responses
                async with bot_listener.response_lock:
                    # Find the most recent response after our message
                    if bot_listener.recent_responses:
                        latest_response = max(
                            bot_listener.recent_responses.values(),
                            key=lambda x: x["date"]
                        )
                        # Check if this response came after our message
                        if latest_response["message_id"] > sent_message.id:
                            response = latest_response
                            break
                
            return {
                "sent_message_id": sent_message.id,
                "response": response
            }
        
        # Run async function
        if listener_loop and listener_loop.is_running():
            future = asyncio.run_coroutine_threadsafe(send_and_wait(), listener_loop)
            result = future.result(timeout=15)
        else:
            return jsonify({
                "success": False,
                "error": "Listener loop not running"
            }), 503
        
        # Extract topupResult status from MongoDB
        status = None
        if bot_listener.mongo_collection is not None:
            try:
                # Wait a bit for MongoDB to save the response (increase wait time)
                time.sleep(1.5)
                
                # Get the response message_id
                response_data = result.get("response")
                message_id = None
                
                if response_data:
                    message_id = response_data.get("message_id")
                    # Check if status is already in response raw_data
                    if response_data.get("raw_data") and response_data["raw_data"].get("topupResult"):
                        status = response_data["raw_data"]["topupResult"].get("status")
                
                # If status not found in response, query MongoDB by message_id
                if not status and message_id:
                    mongo_doc = bot_listener.mongo_collection.find_one({"message_id": message_id})
                    if mongo_doc and mongo_doc.get("topupResult"):
                        status = mongo_doc["topupResult"].get("status")
                
                # If still not found, try to get latest topupResult document
                if not status:
                    # Find latest document with topupResult
                    latest_doc = bot_listener.mongo_collection.find_one(
                        {"topupResult": {"$exists": True}},
                        sort=[("_id", -1)]  # Sort by _id descending (latest first)
                    )
                    if latest_doc and latest_doc.get("topupResult"):
                        # Check if this document is recent (within last 30 seconds)
                        doc_date = latest_doc.get("raw_date")
                        if doc_date:
                            try:
                                doc_datetime = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                                now = datetime.now(doc_datetime.tzinfo) if doc_datetime.tzinfo else datetime.now()
                                if (now - doc_datetime.replace(tzinfo=None)).total_seconds() < 30:
                                    status = latest_doc["topupResult"].get("status")
                            except:
                                # If date parsing fails, use the status anyway
                                status = latest_doc["topupResult"].get("status")
            except Exception as e:
                print(f"Error extracting status from MongoDB: {e}")
                import traceback
                traceback.print_exc()
        
        # Return status (success or failed) or pending if not found
        # If status is "failed", set success to False
        final_status = status or "pending"
        api_success = final_status != "failed"
        
        return jsonify({
            "success": api_success,
            "status": final_status
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "ok",
        "bot_initialized": bot_listener is not None and bot_listener.bot_entity is not None,
        "listener_running": listener_loop is not None and listener_loop.is_running()
    })


@app.route('/')
def index():
    """Serve the index.html page."""
    return send_from_directory('.', 'index.html')


if __name__ == '__main__':
    print("Starting API server...")
    print("Starting bot listener in background...")
    start_listener_thread()
    
    print("API server running on http://localhost:5000")
    print("Endpoints:")
    print("  GET/POST /api/send?command=Krate")
    print("  GET/POST /api/send-message-raw?prefix=ktp&uid=123&diamonds=100")
    print("  GET /health")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

