"""
Flask API Server for Telegram Bot
Provides endpoints to send messages to the bot and receive responses.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import asyncio
import threading
import time
import os
from datetime import datetime
from telegram_listener import TelegramBotListener
from telethon.errors import SessionPasswordNeededError
import config

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Global bot listener instance
bot_listener = None
listener_thread = None
listener_loop = None

# Initialization state tracking
init_error = None
last_init_attempt = None
retry_thread = None
retry_active = False


def check_session_file():
    """Check if session file exists and return information."""
    return config.session_file_exists(), config.get_session_file_info()


def check_and_authenticate():
    """Check if authentication is needed and handle it in main thread.
    
    Returns:
        True if authenticated (or already authenticated), False otherwise
    """
    global init_error, last_init_attempt
    
    print("\n" + "="*80)
    print("Checking Telegram authentication...")
    print("="*80)
    
    # Check session file first
    session_exists, session_info = check_session_file()
    print(f"Session file path: {session_info['path']}")
    print(f"Session file exists: {session_exists}")
    
    if not session_exists:
        error_msg = f"Session file not found at {session_info['path']}"
        print(f"⚠ {error_msg}")
        print("⚠ Please upload a valid session file to the Fly.io volume.")
        init_error = error_msg
        last_init_attempt = datetime.now().isoformat()
        return False
    
    if session_info.get('size', 0) == 0:
        error_msg = f"Session file exists but is empty at {session_info['path']}"
        print(f"⚠ {error_msg}")
        init_error = error_msg
        last_init_attempt = datetime.now().isoformat()
        return False
    
    print(f"✓ Session file found (size: {session_info.get('size', 0)} bytes)")
    if session_info.get('modified'):
        print(f"  Modified: {session_info['modified']}")
    
    # Validate session file using helper function
    temp_listener = TelegramBotListener()
    is_valid, validation_diagnostics = temp_listener.validate_session_file()
    if not is_valid:
        error_msg = f"Session file validation failed: {validation_diagnostics.get('error', 'Unknown error')}"
        print(f"⚠ {error_msg}")
        init_error = error_msg
        last_init_attempt = datetime.now().isoformat()
        return False
    
    try:
        # Reuse the temporary listener instance to check auth status
        
        # Create a new event loop for this check
        check_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(check_loop)
        
        async def check_auth():
            try:
                # Connect to check if we're authorized
                print("  Attempting to connect to Telegram...")
                await temp_listener.client.connect()
                print("  ✓ Connected to Telegram")
                
                # Try to get user info first (better diagnostics)
                try:
                    me = await temp_listener.client.get_me()
                    if me:
                        print(f"✓ Already authenticated! Session file is valid.")
                        print(f"  Connected as: {me.first_name} (@{me.username if me.username else 'no username'})")
                        await temp_listener.client.disconnect()
                        return True
                except Exception as get_me_error:
                    print(f"  ⚠ Could not get user info: {get_me_error}")
                
                # Check if already authorized
                if await temp_listener.client.is_user_authorized():
                    print("✓ Already authenticated! Session file is valid.")
                    await temp_listener.client.disconnect()
                    return True
                else:
                    # Need authentication - check if we're in an interactive environment
                    import sys
                    if not sys.stdin.isatty():
                        # Non-interactive environment (like Fly.io)
                        print("\n⚠ Authentication required but running in non-interactive mode.")
                        print(f"⚠ Session file exists ({session_info.get('size', 0)} bytes) but is not authorized.")
                        print(f"⚠ Session file path: {session_info['path']}")
                        if session_info.get('modified'):
                            print(f"⚠ Session file modified: {session_info['modified']}")
                        print("⚠ This usually means:")
                        print("  1. Session file is expired or invalid")
                        print("  2. Session file is from a different account")
                        print("  3. Session file needs to be re-authenticated")
                        print("⚠ Please authenticate manually by running the app locally first,")
                        print("   then upload the session file to Fly.io volume.")
                        await temp_listener.client.disconnect()
                        return False
                    
                    # Need authentication - run it interactively in main thread
                    print("\n=== Authentication Required ===")
                    print("Please enter your phone number (with country code, e.g., +8801234567890):")
                    phone = input("Phone: ")
                    
                    try:
                        await temp_listener.client.send_code_request(phone)
                        print("\nA verification code has been sent to your Telegram app.")
                        print("Please enter the code:")
                        code = input("Code: ")
                        code = code.strip()  # Remove any whitespace
                        
                        if not code:
                            print("✗ Error: Verification code cannot be empty.")
                            await temp_listener.client.disconnect()
                            return False
                        
                        try:
                            await temp_listener.client.sign_in(phone, code)
                            print("✓ Authentication successful!")
                        except SessionPasswordNeededError:
                            print("\nYour account has 2FA enabled.")
                            print("Please enter your 2FA password:")
                            password = input("Password: ")
                            if not password:
                                print("✗ Error: 2FA password cannot be empty.")
                                await temp_listener.client.disconnect()
                                return False
                            await temp_listener.client.sign_in(password=password)
                            print("✓ Authentication successful!")
                        except Exception as sign_in_error:
                            print(f"✗ Sign in error: {sign_in_error}")
                            print("Please check your verification code and try again.")
                            await temp_listener.client.disconnect()
                            return False
                    except Exception as e:
                        print(f"✗ Authentication error: {e}")
                        print("Please check your phone number and try again.")
                        try:
                            await temp_listener.client.disconnect()
                        except:
                            pass
                        return False
                    
                    # Disconnect after authentication
                    await temp_listener.client.disconnect()
                    print("✓ Session saved. You won't need to authenticate again.")
                    return True
                    
            except KeyboardInterrupt:
                print("\n\n✗ Authentication cancelled by user.")
                try:
                    await temp_listener.client.disconnect()
                except:
                    pass
                return False
            except Exception as e:
                print(f"✗ Error during authentication check: {e}")
                import traceback
                traceback.print_exc()
                try:
                    await temp_listener.client.disconnect()
                except:
                    pass
                return False
        
        # Run the check
        result = check_loop.run_until_complete(check_auth())
        check_loop.close()
        
        return result
        
    except KeyboardInterrupt:
        print("\n\n✗ Authentication cancelled by user.")
        init_error = "Authentication cancelled by user"
        last_init_attempt = datetime.now().isoformat()
        return False
    except Exception as e:
        error_msg = f"Error creating listener for authentication: {e}"
        print(f"✗ {error_msg}")
        print(f"  Session file path: {session_info.get('path', 'unknown')}")
        print(f"  Session file size: {session_info.get('size', 0)} bytes")
        if session_info.get('modified'):
            print(f"  Session file modified: {session_info['modified']}")
        print(f"  Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        init_error = error_msg
        last_init_attempt = datetime.now().isoformat()
        return False


def run_listener():
    """Run the bot listener in a separate thread."""
    global listener_loop, bot_listener, init_error, last_init_attempt
    listener_loop = None
    try:
        listener_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(listener_loop)
        
        async def start_listener():
            global bot_listener, init_error, last_init_attempt
            try:
                print("[Listener] Creating TelegramBotListener instance...")
                bot_listener = TelegramBotListener()
                print("[Listener] Initializing bot listener...")
                # Initialize first (this connects and gets bot_entity)
                await bot_listener.initialize()
                print(f"[Listener] ✓ Bot listener initialized! Bot entity: {bot_listener.bot_entity}")
                # Clear any previous errors on success
                init_error = None
                last_init_attempt = datetime.now().isoformat()
                # Now start listening (this blocks until disconnected)
                print("[Listener] Starting to listen for messages...")
                await bot_listener.start_listening()
            except KeyboardInterrupt:
                print("[Listener] Listener stopped by user")
                init_error = "Listener stopped by user"
            except Exception as e:
                error_msg = f"ERROR during initialization: {e}"
                print(f"[Listener] ✗ {error_msg}")
                import traceback
                traceback.print_exc()
                bot_listener = None
                init_error = error_msg
                last_init_attempt = datetime.now().isoformat()
        
        listener_loop.run_until_complete(start_listener())
    except Exception as e:
        error_msg = f"ERROR in listener thread: {e}"
        print(f"[Listener] ✗ {error_msg}")
        import traceback
        traceback.print_exc()
        global init_error, last_init_attempt
        bot_listener = None
        init_error = error_msg
        last_init_attempt = datetime.now().isoformat()
    finally:
        # Clean up the event loop
        if listener_loop and not listener_loop.is_closed():
            try:
                # Cancel all pending tasks
                try:
                    pending = asyncio.all_tasks(listener_loop)
                    for task in pending:
                        task.cancel()
                    # Run until all tasks are cancelled
                    if pending:
                        listener_loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except RuntimeError:
                    # Loop might be in a bad state, just try to close it
                    pass
                listener_loop.close()
            except Exception as cleanup_error:
                print(f"[Listener] Error during cleanup: {cleanup_error}")


def retry_bot_listener_init():
    """Background thread that retries bot listener initialization."""
    global bot_listener, listener_thread, retry_active, init_error, last_init_attempt
    
    retry_active = True
    retry_count = 0
    max_retries = 100  # Retry up to 100 times (about 50 minutes)
    retry_interval = 30  # Retry every 30 seconds
    
    print(f"[Retry] Starting background retry mechanism (interval: {retry_interval}s)")
    
    while retry_active and retry_count < max_retries:
        time.sleep(retry_interval)
        retry_count += 1
        
        # Check if already initialized
        if bot_listener and bot_listener.bot_entity:
            print("[Retry] Bot listener is initialized. Stopping retry mechanism.")
            retry_active = False
            break
        
        # Check if session file exists
        session_exists, session_info = check_session_file()
        if not session_exists:
            if retry_count % 4 == 0:  # Log every 2 minutes
                print(f"[Retry] Attempt {retry_count}: Session file not found at {session_info['path']}")
            continue
        
        # Try to initialize
        print(f"[Retry] Attempt {retry_count}: Trying to initialize bot listener...")
        print(f"[Retry]   Session file: {session_info.get('path', 'unknown')}")
        print(f"[Retry]   Session file size: {session_info.get('size', 0)} bytes")
        if session_info.get('modified'):
            print(f"[Retry]   Session file modified: {session_info['modified']}")
        last_init_attempt = datetime.now().isoformat()
        
        try:
            # Check if listener thread is still running
            if listener_thread and listener_thread.is_alive():
                print("[Retry] Listener thread is still running, waiting...")
                continue
            
            # If previous thread died, wait a bit before retrying to avoid rapid retries
            if listener_thread and not listener_thread.is_alive():
                print("[Retry] Previous listener thread has died, waiting before retry...")
                time.sleep(2)
            
            # Start new listener thread
            listener_thread = threading.Thread(target=run_listener, daemon=True)
            listener_thread.start()
            
            # Wait longer to see if it initializes (initialization can take 10-15 seconds)
            # Check every second for up to 15 seconds
            initialized = False
            for wait_iter in range(15):
                time.sleep(1)
                if bot_listener and bot_listener.bot_entity:
                    print(f"[Retry] ✓ Bot listener initialized successfully on attempt {retry_count}!")
                    retry_active = False
                    init_error = None
                    initialized = True
                    break
            
            if not initialized:
                print(f"[Retry] Attempt {retry_count} failed. Will retry in {retry_interval}s...")
                # Log detailed error information if available
                if init_error:
                    print(f"[Retry]   Last error: {init_error}")
                # Log session file status
                print(f"[Retry]   Session file status:")
                print(f"[Retry]     - Path: {session_info.get('path', 'unknown')}")
                print(f"[Retry]     - Size: {session_info.get('size', 0)} bytes")
                if session_info.get('modified'):
                    print(f"[Retry]     - Modified: {session_info['modified']}")
                # Validate session file if possible
                try:
                    temp_listener = TelegramBotListener()
                    is_valid, validation_diagnostics = temp_listener.validate_session_file()
                    if not is_valid:
                        print(f"[Retry]     - Validation: FAILED - {validation_diagnostics.get('error', 'Unknown error')}")
                    else:
                        print(f"[Retry]     - Validation: PASSED")
                except Exception as validation_error:
                    print(f"[Retry]     - Validation: Error checking - {validation_error}")
                
        except Exception as e:
            error_msg = f"Retry attempt {retry_count} failed: {e}"
            print(f"[Retry] ✗ {error_msg}")
            print(f"[Retry]   Error type: {type(e).__name__}")
            print(f"[Retry]   Session file: {session_info.get('path', 'unknown')}")
            print(f"[Retry]   Session file size: {session_info.get('size', 0)} bytes")
            import traceback
            traceback.print_exc()
            init_error = error_msg
            last_init_attempt = datetime.now().isoformat()
    
    if retry_count >= max_retries:
        print(f"[Retry] Maximum retry attempts ({max_retries}) reached. Stopping retry mechanism.")
    retry_active = False


def start_listener_thread():
    """Start the bot listener in a background thread."""
    global listener_thread, retry_thread
    listener_thread = threading.Thread(target=run_listener, daemon=True)
    listener_thread.start()
    
    # Wait for listener to initialize (check every 0.5 seconds, max 30 seconds)
    print("[API] Waiting for bot listener to initialize...")
    max_wait = 30
    waited = 0
    while waited < max_wait:
        time.sleep(0.5)
        waited += 0.5
        if bot_listener and bot_listener.bot_entity:
            print(f"[API] Bot listener initialized successfully after {waited:.1f} seconds")
            return
        if waited % 2 == 0:  # Print every 2 seconds
            print(f"[API] Still waiting for bot listener... ({waited:.0f}s)")
    
    if bot_listener and bot_listener.bot_entity:
        print("[API] Bot listener initialized successfully")
    else:
        print("[API] WARNING: Bot listener may not be fully initialized yet")
        # Start retry mechanism in background
        if not retry_thread or not retry_thread.is_alive():
            print("[API] Starting background retry mechanism...")
            retry_thread = threading.Thread(target=retry_bot_listener_init, daemon=True)
            retry_thread.start()


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
            # Register pending request BEFORE sending to ensure we catch the response
            response_event, pending_item = await bot_listener.register_pending_request(uid, None)
            
            # Send message to bot
            sent_message = await bot_listener.client.send_message(
                bot_listener.bot_entity, 
                message
            )
            
            # Update pending request with sent_message_id
            pending_item["sent_message_id"] = sent_message.id
            
            # Wait for UID-matched response (max 10 seconds)
            try:
                # Wait for event to be set (with timeout)
                await asyncio.wait_for(response_event.wait(), timeout=10.0)
                
                # Get the response data from the pending item
                response = pending_item["response_data"]
                
                # Clean up pending request
                await bot_listener.unregister_pending_request(uid, pending_item)
                
                return {
                    "sent_message_id": sent_message.id,
                    "response": response
                }
            except asyncio.TimeoutError:
                # Timeout - clean up pending request
                await bot_listener.unregister_pending_request(uid, pending_item)
                print(f"  [Pending] Timeout waiting for response for UID: {uid}")
                
                # Fallback to old behavior: try to find any response after our message
                response = None
                async with bot_listener.response_lock:
                    if bot_listener.recent_responses:
                        latest_response = max(
                            bot_listener.recent_responses.values(),
                            key=lambda x: x["date"]
                        )
                        # Check if this response came after our message
                        if latest_response["message_id"] > sent_message.id:
                            response = latest_response
                
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
        
        # Extract topupResult data from MongoDB
        status = None
        uid = None
        used_uc_cards = []
        topup_result_doc = None
        
        if bot_listener.mongo_collection is not None:
            try:
                # Wait a bit for MongoDB to save the response (increase wait time)
                time.sleep(1.5)
                
                # Get the response message_id
                response_data = result.get("response")
                message_id = None
                
                if response_data:
                    message_id = response_data.get("message_id")
                    # Check if topupResult is already in response raw_data
                    if response_data.get("raw_data") and response_data["raw_data"].get("topupResult"):
                        topup_result_doc = response_data["raw_data"]["topupResult"]
                        status = topup_result_doc.get("status")
                        if topup_result_doc.get("user"):
                            uid = topup_result_doc["user"].get("uid")
                        if topup_result_doc.get("payment") and topup_result_doc["payment"].get("usedUc"):
                            used_uc_obj = topup_result_doc["payment"]["usedUc"]
                            if isinstance(used_uc_obj, dict) and used_uc_obj.get("codes"):
                                used_uc_cards = [card.get("code") for card in used_uc_obj["codes"] if card.get("code")]
                            elif isinstance(used_uc_obj, list):
                                used_uc_cards = [card.get("code") if isinstance(card, dict) else str(card) for card in used_uc_obj]
                
                # If not found in response, query MongoDB by message_id
                if not topup_result_doc and message_id:
                    mongo_doc = bot_listener.mongo_collection.find_one({"message_id": message_id})
                    if mongo_doc and mongo_doc.get("topupResult"):
                        topup_result_doc = mongo_doc["topupResult"]
                        status = topup_result_doc.get("status")
                        if topup_result_doc.get("user"):
                            uid = topup_result_doc["user"].get("uid")
                        if topup_result_doc.get("payment") and topup_result_doc["payment"].get("usedUc"):
                            used_uc_obj = topup_result_doc["payment"]["usedUc"]
                            if isinstance(used_uc_obj, dict) and used_uc_obj.get("codes"):
                                used_uc_cards = [card.get("code") for card in used_uc_obj["codes"] if card.get("code")]
                            elif isinstance(used_uc_obj, list):
                                used_uc_cards = [card.get("code") if isinstance(card, dict) else str(card) for card in used_uc_obj]
                
                # If still not found, try to get latest topupResult document
                if not topup_result_doc:
                    # Find latest document with topupResult
                    latest_doc = bot_listener.mongo_collection.find_one(
                        {"topupResult": {"$exists": True}},
                        sort=[("_id", -1)]  # Sort by _id descending (latest first)
                    )
                    if latest_doc and latest_doc.get("topupResult"):
                        # Check if this document is recent (within last 30 seconds)
                        doc_date = latest_doc.get("raw_date")
                        use_this_doc = False
                        if doc_date:
                            try:
                                doc_datetime = datetime.fromisoformat(doc_date.replace('Z', '+00:00'))
                                now = datetime.now(doc_datetime.tzinfo) if doc_datetime.tzinfo else datetime.now()
                                if (now - doc_datetime.replace(tzinfo=None)).total_seconds() < 30:
                                    use_this_doc = True
                            except:
                                # If date parsing fails, use the document anyway
                                use_this_doc = True
                        
                        if use_this_doc:
                            topup_result_doc = latest_doc["topupResult"]
                            status = topup_result_doc.get("status")
                            if topup_result_doc.get("user"):
                                uid = topup_result_doc["user"].get("uid")
                            if topup_result_doc.get("payment") and topup_result_doc["payment"].get("usedUc"):
                                used_uc_obj = topup_result_doc["payment"]["usedUc"]
                                if isinstance(used_uc_obj, dict) and used_uc_obj.get("codes"):
                                    used_uc_cards = [card.get("code") for card in used_uc_obj["codes"] if card.get("code")]
                                elif isinstance(used_uc_obj, list):
                                    used_uc_cards = [card.get("code") if isinstance(card, dict) else str(card) for card in used_uc_obj]
            except Exception as e:
                print(f"Error extracting topupResult from MongoDB: {e}")
                import traceback
                traceback.print_exc()
        
        # Return status, uid, and usedUc cards
        # If status is "failed", set success to False
        final_status = status or "pending"
        api_success = final_status != "failed"
        
        response_data = {
            "success": api_success,
            "status": final_status
        }
        
        # Add uid if available
        if uid:
            response_data["uid"] = uid
        
        # Add usedUc cards if available
        if used_uc_cards:
            response_data["usedUc"] = used_uc_cards
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint with diagnostic information."""
    session_exists, session_info = check_session_file()
    bot_initialized = bot_listener is not None and bot_listener.bot_entity is not None
    # Use thread alive status + bot initialization instead of loop.is_running()
    # because is_running() may return False when loop is waiting for events
    listener_running = (
        listener_thread is not None and 
        listener_thread.is_alive() and 
        bot_listener is not None and 
        bot_listener.bot_entity is not None
    )
    
    response = {
        "status": "ok",
        "bot_initialized": bot_initialized,
        "listener_running": listener_running,
        "session_file": {
            "exists": session_exists,
            "path": session_info.get("path", "unknown")
        }
    }
    
    # Add diagnostic information if bot is not initialized
    if not bot_initialized:
        response["diagnostics"] = {
            "init_error": init_error,
            "last_init_attempt": last_init_attempt,
            "retry_active": retry_active,
            "session_file_size": session_info.get("size", 0),
            "session_file_modified": session_info.get("modified"),
            "listener_thread_alive": listener_thread.is_alive() if listener_thread else False,
            "listener_loop_running": listener_loop.is_running() if listener_loop else False,
            "listener_loop_exists": listener_loop is not None
        }
    
    return jsonify(response)


@app.route('/api/status', methods=['GET'])
def status_check():
    """Detailed status endpoint with full diagnostic information."""
    session_exists, session_info = check_session_file()
    bot_initialized = bot_listener is not None and bot_listener.bot_entity is not None
    # Use thread alive status + bot initialization instead of loop.is_running()
    # because is_running() may return False when loop is waiting for events
    listener_running = (
        listener_thread is not None and 
        listener_thread.is_alive() and 
        bot_listener is not None and 
        bot_listener.bot_entity is not None
    )
    
    response = {
        "status": "ok" if bot_initialized else "degraded",
        "bot_initialized": bot_initialized,
        "listener_running": listener_running,
        "session_file": session_info,
        "initialization": {
            "error": init_error,
            "last_attempt": last_init_attempt,
            "retry_active": retry_active,
            "listener_thread_alive": listener_thread.is_alive() if listener_thread else False
        },
        "bot_info": {
            "bot_entity": str(bot_listener.bot_entity) if bot_listener and bot_listener.bot_entity else None,
            "bot_username": config.BOT_USERNAME
        }
    }
    
    return jsonify(response)


@app.route('/')
def index():
    """Serve the index.html page."""
    return send_from_directory('.', 'index.html')


if __name__ == '__main__':
    print("Starting API server...")
    
    # Step 1: Check and authenticate if needed (in main thread, interactive)
    # In non-interactive mode (Fly.io), allow app to start even if auth fails
    # The health endpoint will show bot_initialized: false
    auth_success = check_and_authenticate()
    if not auth_success:
        import sys
        if not sys.stdin.isatty():
            # Non-interactive mode - allow app to start but bot won't work
            print("\n⚠ Warning: Authentication failed in non-interactive mode.")
            print("⚠ API server will start, but bot listener will not be initialized.")
            print("⚠ Please upload a valid session file to /app/sessions/telegram_listener.session")
        else:
            # Interactive mode - exit if auth fails
            print("\n✗ Authentication failed. Cannot start API server.")
            print("Please fix authentication issues and try again.")
            exit(1)
    
    # Step 2: Start bot listener in background thread (only if authenticated)
    if auth_success:
        print("\n" + "="*80)
        print("Starting bot listener in background...")
        print("="*80)
        start_listener_thread()
    else:
        print("\n⚠ Skipping bot listener initialization (authentication check failed)")
        # Start retry mechanism to attempt initialization when session file is available
        # This is important because check_and_authenticate() might fail in non-interactive mode
        # even if the session file is valid, so we let the retry mechanism try actual initialization
        session_exists, session_info = check_session_file()
        if session_exists:
            print(f"⚠ Session file exists at {session_info['path']} (size: {session_info.get('size', 0)} bytes)")
            print(f"⚠ Starting retry mechanism to attempt initialization...")
            print(f"⚠ Note: check_and_authenticate() may fail in non-interactive mode,")
            print(f"   but the retry mechanism will attempt actual initialization which may succeed.")
            if not retry_thread or not retry_thread.is_alive():
                retry_thread = threading.Thread(target=retry_bot_listener_init, daemon=True)
                retry_thread.start()
        else:
            print(f"⚠ Session file not found at {session_info['path']}")
            print(f"⚠ Please upload session file to enable bot listener initialization")
            print(f"⚠ Upload command: fly ssh sftp shell -a tg-bot-lisener")
    
    # Step 3: Start Flask server
    port = int(os.getenv("PORT", "5000"))
    print("\n" + "="*80)
    print(f"API server running on http://0.0.0.0:{port}")
    print("Endpoints:")
    print("  GET/POST /api/send?command=Krate")
    print("  GET/POST /api/send-message-raw?prefix=ktp&uid=123&diamonds=100")
    print("  GET /health")
    print("="*80 + "\n")
    
    app.run(host='0.0.0.0', port=port, debug=False)

