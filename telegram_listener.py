"""
Telegram Bot Response Listener
Listens to messages from a specific Telegram bot and prints them to console.
Also saves filtered messages to MongoDB.
"""

import asyncio
import re
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import config


class TelegramBotListener:
    def __init__(self):
        self.client = TelegramClient(
            config.SESSION_NAME,
            config.API_ID,
            config.API_HASH
        )
        self.bot_username = config.BOT_USERNAME
        self.bot_entity = None
        self.mongo_client = None
        self.mongo_db = None
        self.mongo_collection = None
        # Store recent responses for API access
        self.recent_responses = {}
        self.response_lock = asyncio.Lock()

    def connect_mongodb(self):
        """Connect to MongoDB."""
        try:
            print(f"Connecting to MongoDB at {config.MONGODB_HOST}:{config.MONGODB_PORT}...")
            self.mongo_client = MongoClient(
                host=config.MONGODB_HOST,
                port=config.MONGODB_PORT,
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            self.mongo_client.server_info()
            self.mongo_db = self.mongo_client[config.MONGODB_DATABASE]
            self.mongo_collection = self.mongo_db[config.MONGODB_COLLECTION]
            print(f"✓ Successfully connected to MongoDB!")
            print(f"  Database: {config.MONGODB_DATABASE}")
            print(f"  Collection: {config.MONGODB_COLLECTION}")
            return True
        except ConnectionFailure as e:
            print(f"✗ ERROR: Could not connect to MongoDB: {e}")
            print("  Make sure MongoDB is running on localhost:27017")
            print("  Messages will still be printed to console, but not saved to database.")
            self.mongo_client = None
            self.mongo_collection = None
            return False
        except Exception as e:
            print(f"✗ ERROR: MongoDB connection error: {e}")
            print(f"  Error type: {type(e).__name__}")
            self.mongo_client = None
            self.mongo_collection = None
            return False

    async def initialize(self):
        """Initialize the Telegram client and authenticate."""
        print("Connecting to Telegram...")
        
        # Connect to MongoDB first
        self.connect_mongodb()
        
        # Connect first
        await self.client.connect()
        
        # Check if we need to authenticate
        if not await self.client.is_user_authorized():
            print("\n=== First Time Setup ===")
            print("Please enter your phone number (with country code, e.g., +8801234567890):")
            phone = input("Phone: ")
            
            try:
                await self.client.send_code_request(phone)
                print("\nA verification code has been sent to your Telegram app.")
                print("Please enter the code:")
                code = input("Code: ")
                code = code.strip()  # Remove any whitespace
                
                try:
                    await self.client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    print("\nYour account has 2FA enabled.")
                    print("Please enter your 2FA password:")
                    password = input("Password: ")
                    await self.client.sign_in(password=password)
            except Exception as e:
                print(f"Authentication error: {e}")
                raise
        
        print("Successfully connected to Telegram!")
        
        # Get bot entity
        try:
            self.bot_entity = await self.client.get_entity(self.bot_username)
            print(f"Bot found: {self.bot_entity.first_name} (@{self.bot_username})")
        except Exception as e:
            print(f"Error finding bot @{self.bot_username}: {e}")
            print("Please check the bot username in config.py")
            raise

    def extract_message_data(self, message):
        """Extract message data for MongoDB storage."""
        message_data = {
            "message_id": message.id,
            "date": message.date.isoformat() if message.date else datetime.now().isoformat(),
            "sender_id": message.sender_id,
            "chat_id": message.chat_id if hasattr(message, 'chat_id') else None,
            "message_type": "text",
            "media_type": None,
            "text": message.text if message.text else "",
            "raw_date": datetime.now().isoformat()
        }
        
        # Handle different media types
        if message.photo:
            message_data["message_type"] = "photo"
            message_data["media_type"] = "photo"
        elif message.video:
            message_data["message_type"] = "video"
            message_data["media_type"] = "video"
        elif message.audio:
            message_data["message_type"] = "audio"
            message_data["media_type"] = "audio"
        elif message.document:
            message_data["message_type"] = "document"
            message_data["media_type"] = message.document.mime_type if message.document.mime_type else "document"
        elif message.sticker:
            message_data["message_type"] = "sticker"
            message_data["media_type"] = "sticker"
        elif message.voice:
            message_data["message_type"] = "voice"
            message_data["media_type"] = "voice"
        
        return message_data

    def format_message(self, message):
        """Format message for console output."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sender = "Bot"
        content = message.text if message.text else "[Media/Sticker/Other]"
        
        # Handle media messages
        if message.photo:
            content = f"[Photo] {content}"
        elif message.video:
            content = f"[Video] {content}"
        elif message.audio:
            content = f"[Audio] {content}"
        elif message.document:
            content = f"[Document: {message.document.mime_type}] {content}"
        elif message.sticker:
            content = f"[Sticker] {content}"
        
        return f"[{timestamp}] {sender}: {content}"

    def extract_uc_bank_data(self, text):
        """Extract UC and BANK/PCS numbers from text lines."""
        # Pattern to match: "20 UC ⇨ 19 BANK" or "161 UC ⇨ 178 PCS"
        # Supports various arrow symbols: ⇨, →, ->, =>
        pattern = r'(\d+)\s*UC\s*[⇨→\->=]+\s*(\d+)\s*(BANK|PCS|bank|pcs)'
        
        matches = re.findall(pattern, text, re.IGNORECASE)
        uc_bank_pairs = []
        
        for match in matches:
            uc_value = int(match[0])
            bank_value = int(match[1])
            unit = match[2].upper()
            
            uc_bank_pairs.append({
                "uc": uc_value,
                "bank": bank_value,
                "unit": unit
            })
        
        return uc_bank_pairs

    def parse_account_status(self, text):
        """Parse account status from bot response.
        
        Returns structured data or None if format doesn't match.
        """
        if not text:
            return None
        
        # Debug: Print what we're trying to parse
        print(f"  [Debug] Parsing text: {text[:100]}...")
        
        # Clean the text - remove separator lines
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip separator lines and empty lines
            if not line or re.match(r'^[▔═\-_]+$', line):
                continue
            cleaned_lines.append(line)
        
        account_status = {
            "user": {"name": None},
            "wallet": {},
            "currency": "Tk"
        }
        
        # Check if this looks like an account status message
        # It should have NAME/DUE/BALANCE/DUE LIMIT fields
        has_account_fields = False
        for line in cleaned_lines:
            line_lower = line.lower()
            if any(field in line_lower for field in ['name', 'due', 'balance', 'limit']):
                has_account_fields = True
                break
        
        if not has_account_fields:
            print(f"  [Debug] No account fields found in message")
            return None
        
        # Process each line
        for line in cleaned_lines:
            # Check if line contains account information
            # Handle both formats: "NAME : Mohammad Robayet" and "➪ Nᴀᴍᴇ : Mohammad Robayet"
            if ':' not in line:
                continue
                
            # Split by colon
            parts = line.split(':', 1)
            if len(parts) < 2:
                continue
            
            field_name = parts[0].strip().lower()
            field_value = parts[1].strip()
            
            print(f"  [Debug] Found field: '{field_name}' = '{field_value}'")
            
            # Handle name field
            if 'name' in field_name:
                # Extract just the name (remove any trailing numbers/currency)
                name_match = re.search(r'([a-zA-Z\s]+)', field_value)
                if name_match:
                    account_status["user"]["name"] = name_match.group(1).strip()
                    print(f"  [Debug] Extracted name: {account_status['user']['name']}")
            
            # Handle due field (not due limit)
            elif 'due' in field_name and 'limit' not in field_name:
                # Handle G9.0 -> 69.0 conversion (G might be typo for 6)
                field_value = field_value.replace('G', '6').replace('g', '6')
                value_match = re.search(r'([\d.]+)', field_value)
                if value_match:
                    try:
                        account_status["wallet"]["due"] = float(value_match.group(1))
                        print(f"  [Debug] Extracted due: {account_status['wallet']['due']}")
                    except ValueError:
                        print(f"  [Debug] Could not parse due value: {field_value}")
            
            # Handle balance field
            elif 'balance' in field_name:
                value_match = re.search(r'([\d.]+)', field_value)
                if value_match:
                    try:
                        account_status["wallet"]["balance"] = float(value_match.group(1))
                        print(f"  [Debug] Extracted balance: {account_status['wallet']['balance']}")
                    except ValueError:
                        print(f"  [Debug] Could not parse balance value: {field_value}")
            
            # Handle due limit field
            elif 'due' in field_name and 'limit' in field_name:
                value_match = re.search(r'([\d.]+)', field_value)
                if value_match:
                    try:
                        account_status["wallet"]["dueLimit"] = float(value_match.group(1))
                        print(f"  [Debug] Extracted dueLimit: {account_status['wallet']['dueLimit']}")
                    except ValueError:
                        print(f"  [Debug] Could not parse dueLimit value: {field_value}")
        
        # Check if we extracted a name
        if account_status["user"]["name"]:
            print(f"  [Debug] Successfully parsed account status for: {account_status['user']['name']}")
            return account_status
        
        print(f"  [Debug] No name extracted, returning None")
        return None
    def parse_price_list(self, text):
        """Parse price list from bot response.
        
        Expected format:
        ☞ 20   🆄🅲  ➪  19  Bᴀɴᴋ
        ☞ Weekly Lite  ➪ 40.0 Bᴀɴᴋ
        ☞ Level Up-6   ➪ 35.0 Bᴀɴᴋ
        ☞ Evo 3 Day   ➪ 66.0 Bᴀɴᴋ
        
        Returns structured data with ucPriceList and specialPackages arrays, or None if format doesn't match.
        """
        if not text:
            return None
        
        uc_price_list = []
        special_packages = []
        
        # Pattern for UC prices: ☞ 20   🆄🅲  ➪  19  Bᴀɴᴋ
        # Match: ☞ followed by number, then 🆄🅲 (or UC), then ➪, then number, then Bᴀɴᴋ
        # Handle both Unicode emoji (🆄🅲) and regular text (UC)
        uc_pattern = r'☞\s*(\d+)\s*(?:🆄\s*🅲|🆄🅲|[UC]+)\s*➪\s*(\d+)\s*B[ᴀɴᴋANK]+'
        uc_matches = re.findall(uc_pattern, text, re.IGNORECASE)
        
        for match in uc_matches:
            try:
                amount = int(match[0])
                price = int(match[1])
                uc_price_list.append({
                    "type": "uc",
                    "amount": amount,
                    "price": price,
                    "payment": "bank"
                })
            except (ValueError, IndexError):
                continue
        
        # Pattern for Weekly Lite: ☞ Weekly Lite  ➪ 40.0 Bᴀɴᴋ
        weekly_pattern = r'☞\s*Weekly\s+Lite\s*➪\s*([\d.]+)\s*B[ᴀɴᴋANK]+'
        weekly_match = re.search(weekly_pattern, text, re.IGNORECASE)
        if weekly_match:
            try:
                price = float(weekly_match.group(1))
                special_packages.append({
                    "type": "weekly",
                    "name": "Weekly Lite",
                    "price": price,
                    "payment": "bank"
                })
            except (ValueError, IndexError):
                pass
        
        # Pattern for Level Up packages: ☞ Level Up-6   ➪ 35.0 Bᴀɴᴋ
        level_up_pattern = r'☞\s*Level\s+Up-(\d+)\s*➪\s*([\d.]+)\s*B[ᴀɴᴋANK]+'
        level_up_matches = re.findall(level_up_pattern, text, re.IGNORECASE)
        for match in level_up_matches:
            try:
                level = int(match[0])
                price = float(match[1])
                special_packages.append({
                    "type": "level-up",
                    "name": f"Level Up {level}",
                    "price": price,
                    "payment": "bank"
                })
            except (ValueError, IndexError):
                continue
        
        # Pattern for Evo packages: ☞ Evo 3 Day   ➪ 66.0 Bᴀɴᴋ
        evo_pattern = r'☞\s*Evo\s+(\d+)\s+Day\s*➪\s*([\d.]+)\s*B[ᴀɴᴋANK]+'
        evo_matches = re.findall(evo_pattern, text, re.IGNORECASE)
        for match in evo_matches:
            try:
                days = int(match[0])
                price = float(match[1])
                special_packages.append({
                    "type": "evo",
                    "name": f"Evo {days} Day",
                    "price": price,
                    "payment": "bank"
                })
            except (ValueError, IndexError):
                continue
        
        # Only return if we found at least one UC price or special package
        if uc_price_list or special_packages:
            return {
                "ucPriceList": uc_price_list,
                "specialPackages": special_packages
            }
        
        return None

    def parse_topup_result(self, text):
        """Parse TOPUP DONE message from bot response.
        
        Expected format:
        ✅ Monthly 💎 TOPUP DONE
        ┌──────────────────────────┐
        │ Order ID : #2237
        │ User   : ツOɴʟʏ⸙ᴢ!xᴜ모
        │ UID    : 2194747891
        └──────────────────────────┘
        BDMB-S-S-02536618 5494-2393-2291-4243  ✅ Success
        BDMB-S-S-02539602 1251-3736-3127-9172  ✅ Success
        ...
        ┌──────────────────────────┐
        │ Total  : 2934.0৳ ৳ (0.5৳ Fee/Unit)
        │ Monthly  : 4x
        │ Baki   : 2934.00৳
        │ Due    : 0.00 + 2934.00 = 2934.00৳
        │ 
        │ Duration : 5.47s
        └── 🤖 Powered by UcBot ───┘
        
        Returns structured data or None if format doesn't match.
        """
        if not text:
            return None
        
        # Check if this is a TOPUP DONE message or Limit Over message
        is_topup_done = "TOPUP DONE" in text.upper()
        is_limit_over = "LIMIT OVER" in text.upper() or "🚫" in text
        
        if not is_topup_done and not is_limit_over:
            return None
        
        if is_limit_over:
            print(f"  [Debug] Parsing Limit Over message...")
            # For Limit Over, return minimal structure with failed status
            topup_result = {
                "status": "failed",
                "orderId": None
            }
            
            # Try to extract Order ID if present
            order_id_match = re.search(r'Order\s+ID\s*:\s*#?(\d+)', text, re.IGNORECASE)
            if order_id_match:
                try:
                    topup_result["orderId"] = int(order_id_match.group(1))
                    print(f"  [Debug] Extracted orderId: {topup_result['orderId']}")
                except ValueError:
                    pass
            
            # Return minimal structure for Limit Over
            return topup_result
        
        print(f"  [Debug] Parsing TOPUP DONE message...")
        
        topup_result = {
            "status": "success",
            "orderId": None,
            "user": {
                "name": None,
                "uid": None
            },
            "product": {
                "type": "diamond",
                "quantity": None,
                "unitPrice": None
            },
            "payment": {
                "usedUc": [],
                "feePerUnit": None,
                "total": None,
                "paid": None,
                "due": None
            },
            "meta": {
                "durationSec": None,
                "provider": "UcBot"
            }
        }
        
        # Extract Order ID: Order ID : #2237
        order_id_match = re.search(r'Order\s+ID\s*:\s*#?(\d+)', text, re.IGNORECASE)
        if order_id_match:
            try:
                topup_result["orderId"] = int(order_id_match.group(1))
                print(f"  [Debug] Extracted orderId: {topup_result['orderId']}")
            except ValueError:
                pass
        
        # Extract User name: User   : ツOɴʟʏ⸙ᴢ!xᴜ모
        user_match = re.search(r'User\s*:\s*(.+)', text, re.IGNORECASE)
        if user_match:
            user_name = user_match.group(1).strip()
            # Remove any trailing box drawing characters or separators
            user_name = re.sub(r'[└┘┌┐│─━┃┏┓┗┛├┤┬┴┼╭╮╯╰╱╲╳]+', '', user_name).strip()
            if user_name:
                topup_result["user"]["name"] = user_name
                print(f"  [Debug] Extracted user name: {topup_result['user']['name']}")
        
        # Extract UID: UID    : 2194747891
        uid_match = re.search(r'UID\s*:\s*(\d+)', text, re.IGNORECASE)
        if uid_match:
            topup_result["user"]["uid"] = uid_match.group(1)
            print(f"  [Debug] Extracted UID: {topup_result['user']['uid']}")
        
        # Extract UC Cards: 
        # BDMB-S-S-02536618 5494-2393-2291-4243  ✅ Success
        # BDMB-T-S-01458610 1146-2271-5996-5120  ✅ Success
        # UPBD-G-S-03504383 2137-4322-5341-2648  ✅ Success
        # Parse line by line to find UC card lines
        # Supports multiple prefixes: BDMB, UPBD, and any 4-letter prefix
        uc_cards = []
        lines = text.split('\n')
        
        print(f"  [Debug] Looking for UC cards in {len(lines)} lines...")
        
        # More flexible pattern to match UC card codes
        # Pattern breakdown:
        # - (BDMB|UPBD|[A-Z]{4}) : BDMB, UPBD, or any 4 uppercase letters
        # - [-\w]+ : code part with dashes and alphanumeric (e.g., -T-S-01458610)
        # - \s+ : one or more spaces
        # - [\d-]+ : card number with dashes (e.g., 1146-2271-5996-5120)
        uc_card_pattern = r'((?:BDMB|UPBD|[A-Z]{4})[-\w]+\s+[\d-]+)'
        
        for line_num, line in enumerate(lines, 1):
            original_line = line
            line = line.strip()
            
            # Check if line contains UC card indicators
            has_uc_prefix = bool(re.search(r'(BDMB|UPBD|[A-Z]{4})[-\w]+\s+[\d-]+', line, re.IGNORECASE))
            has_success = '✅' in line or '✓' in line or 'Success' in line.upper()
            
            if has_uc_prefix:
                print(f"  [Debug] Line {line_num} contains UC prefix: {line[:80]}")
                
                # Try to extract UC card code
                card_match = re.search(uc_card_pattern, line, re.IGNORECASE)
                if card_match:
                    card_str = card_match.group(1)
                    # Normalize spaces
                    card_str = re.sub(r'\s+', ' ', card_str.strip())
                    if card_str not in uc_cards:  # Avoid duplicates
                        uc_cards.append(card_str)
                        print(f"  [Debug]   Found UC card: {card_str}")
                else:
                    print(f"  [Debug]   Pattern didn't match line: {line[:80]}")
        
        # Also try searching entire text if line-by-line didn't work
        if not uc_cards:
            print(f"  [Debug] Line-by-line search found nothing, trying full text search...")
            # More comprehensive pattern for full text search
            full_text_pattern = r'((?:BDMB|UPBD|[A-Z]{4})[-\w]+\s+[\d-]+)'
            all_matches = re.findall(full_text_pattern, text, re.IGNORECASE)
            if all_matches:
                print(f"  [Debug] Found {len(all_matches)} potential UC cards in full text")
                for match in all_matches:
                    card_str = re.sub(r'\s+', ' ', match.strip())
                    if card_str not in uc_cards:
                        uc_cards.append(card_str)
                        print(f"  [Debug]   Found UC card: {card_str}")
        
        if uc_cards:
            # Convert string array to array of objects
            # Each UC card will be an object with "code" field
            uc_card_objects = []
            for card_str in uc_cards:
                uc_card_objects.append({
                    "code": card_str
                })
            
            # usedUc will be an object containing an array
            topup_result["payment"]["usedUc"] = {
                "codes": uc_card_objects
            }
            print(f"  [Debug] Extracted {len(uc_card_objects)} UC cards")
            for i, card_obj in enumerate(uc_card_objects, 1):
                print(f"  [Debug]   Card {i}: {card_obj['code']}")
        else:
            print(f"  [Debug] No UC cards found in message")
            print(f"  [Debug] Message preview (first 500 chars): {text[:500]}")
        
        # Extract Total: Total  : 2934.0৳ ৳ (0.5৳ Fee/Unit)
        total_match = re.search(r'Total\s*:\s*([\d.]+)', text, re.IGNORECASE)
        if total_match:
            try:
                topup_result["payment"]["total"] = float(total_match.group(1))
                print(f"  [Debug] Extracted total: {topup_result['payment']['total']}")
            except ValueError:
                pass
        
        # Extract Fee per Unit: (0.5৳ Fee/Unit)
        fee_match = re.search(r'\(([\d.]+)\s*[৳Tk]+\s*Fee/Unit\)', text, re.IGNORECASE)
        if fee_match:
            try:
                topup_result["payment"]["feePerUnit"] = float(fee_match.group(1))
                print(f"  [Debug] Extracted feePerUnit: {topup_result['payment']['feePerUnit']}")
            except ValueError:
                pass
        
        # Extract Monthly count: Monthly  : 4x
        monthly_match = re.search(r'Monthly\s*:\s*(\d+)x?', text, re.IGNORECASE)
        if monthly_match:
            try:
                quantity = int(monthly_match.group(1))
                topup_result["product"]["quantity"] = quantity
                print(f"  [Debug] Extracted quantity: {topup_result['product']['quantity']}")
                
                # Calculate unitPrice from total and quantity
                if topup_result["payment"]["total"] and quantity > 0:
                    topup_result["product"]["unitPrice"] = topup_result["payment"]["total"] / quantity
                    print(f"  [Debug] Calculated unitPrice: {topup_result['product']['unitPrice']}")
            except (ValueError, ZeroDivisionError):
                pass
        
        # Extract Baki: Baki   : 2934.00৳
        baki_match = re.search(r'Baki\s*:\s*([\d.]+)', text, re.IGNORECASE)
        if baki_match:
            try:
                baki = float(baki_match.group(1))
                # Baki is the remaining amount, which is the same as due
                topup_result["payment"]["due"] = baki
                print(f"  [Debug] Extracted due (from Baki): {topup_result['payment']['due']}")
            except ValueError:
                pass
        
        # Extract Due: Due    : 0.00 + 2934.00 = 2934.00৳
        # This format shows: previous_due + new_due = total_due
        due_match = re.search(r'Due\s*:\s*([\d.]+)\s*\+\s*([\d.]+)\s*=\s*([\d.]+)', text, re.IGNORECASE)
        if due_match:
            try:
                # Use the final due amount (after =)
                total_due = float(due_match.group(3))
                topup_result["payment"]["due"] = total_due
                print(f"  [Debug] Extracted due: {topup_result['payment']['due']}")
            except ValueError:
                pass
        
        # Calculate paid amount: paid = total - due
        if topup_result["payment"]["total"] is not None and topup_result["payment"]["due"] is not None:
            topup_result["payment"]["paid"] = topup_result["payment"]["total"] - topup_result["payment"]["due"]
            print(f"  [Debug] Calculated paid: {topup_result['payment']['paid']}")
        
        # Extract Duration: Duration : 5.47s
        duration_match = re.search(r'Duration\s*:\s*([\d.]+)\s*s', text, re.IGNORECASE)
        if duration_match:
            try:
                topup_result["meta"]["durationSec"] = float(duration_match.group(1))
                print(f"  [Debug] Extracted duration: {topup_result['meta']['durationSec']}s")
            except ValueError:
                pass
        
        # Check if we have at least orderId and user info to consider this a valid topup result
        if topup_result["orderId"] and topup_result["user"]["name"]:
            print(f"  [Debug] Successfully parsed TOPUP DONE for order #{topup_result['orderId']}")
            return topup_result
        
        print(f"  [Debug] Incomplete TOPUP DONE data, returning None")
        return None

    def remove_emojis_except_uc(self, text):
        """Remove all emojis from text except 🆄🅲 emoji.
        
        Args:
            text: Input text that may contain emojis
            
        Returns:
            Text with all emojis removed except 🆄 (U+1F194) and 🅲 (U+1F172)
        """
        if not text:
            return text
        
        # Unicode ranges for emojis (comprehensive pattern)
        # This covers most emoji ranges in Unicode
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags (iOS)
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"   # enclosed characters
            "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
            "\U0001FA00-\U0001FA6F"  # chess symbols
            "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
            "\U00002600-\U000026FF"  # miscellaneous symbols
            "\U00002700-\U000027BF"  # dingbats
            "\U0001F018-\U0001F270"  # various asian characters
            "\U0001F300-\U0001F5FF"  # misc symbols and pictographs
            "\U0001F680-\U0001F6FF"  # transport and map
            "\U0001F1E6-\U0001F1FF"  # regional indicator symbols
            "\U0001F191-\U0001F19A"  # enclosed characters
            "\U0001F200-\U0001F2FF"  # enclosed CJK letters and months
            "\U0001F300-\U0001F5FF"  # misc symbols
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F680-\U0001F6FF"  # transport and map
            "\U00002600-\U000026FF"  # misc symbols
            "\U00002700-\U000027BF"  # dingbats
            "\U0001F900-\U0001F9FF"  # supplemental symbols
            "\U0001FA00-\U0001FA6F"  # chess symbols
            "\U0001FA70-\U0001FAFF"  # symbols extended-A
            "]+", 
            flags=re.UNICODE
        )
        
        # Temporarily replace 🆄 and 🅲 with placeholders
        placeholder_uc = "___UC_EMOJI___"
        placeholder_c = "___C_EMOJI___"
        
        # Replace 🆄 and 🅲 with placeholders
        text = text.replace('🆄', placeholder_uc)
        text = text.replace('🅲', placeholder_c)
        
        # Remove all other emojis
        text = emoji_pattern.sub('', text)
        
        # Restore 🆄 and 🅲
        text = text.replace(placeholder_uc, '🆄')
        text = text.replace(placeholder_c, '🅲')
        
        return text

    def save_to_mongodb(self, message_data):
        """Save message data to MongoDB - all text in one document per message_id."""
        if self.mongo_collection is None:
            print("  [MongoDB] Collection not available, skipping save")
            return None
            
        try:
            # Check if message already exists
            existing = self.mongo_collection.find_one({"message_id": message_data["message_id"]})
            
            # Parse account status, price list, and topup result if present
            account_status = None
            price_list = None
            topup_result = None
            
            # Check if topup_result was already parsed in message_handler
            if "_parsed_topup_result" in message_data:
                topup_result = message_data["_parsed_topup_result"]
                print(f"  [MongoDB] Using pre-parsed topup_result")
            
            message_text = message_data.get("text", "")
            
            if message_text:
                # Remove emojis except 🆄🅲 before parsing and saving
                message_text = self.remove_emojis_except_uc(message_text)
                
                # Try to parse topup result if not already parsed
                if not topup_result:
                    topup_result = self.parse_topup_result(message_text)
                
                # Try to parse account status
                account_status = self.parse_account_status(message_text)
                
                # Try to parse price list
                price_list = self.parse_price_list(message_text)
                
                # If any structured data is found, set text to None
                if topup_result or account_status or price_list:
                    print(f"  [MongoDB] Structured data found, setting text to None")
                    message_text = None
        
            if existing:
                # Message already exists - update with structured data
                update_fields = {}
                
                if topup_result:
                    update_fields["topupResult"] = topup_result
                    update_fields["text"] = None
                    print(f"  [MongoDB] Will update with topupResult")
                    
                if account_status:
                    update_fields["account_status"] = account_status
                    update_fields["text"] = None
                    print(f"  [MongoDB] Will update with account_status")
                    
                if price_list:
                    update_fields["price_list"] = price_list
                    update_fields["text"] = None
                    print(f"  [MongoDB] Will update with price_list")
                
                if update_fields:
                    update_result = self.mongo_collection.update_one(
                        {"message_id": message_data["message_id"]},
                        {"$set": update_fields}
                    )
                    if update_result.modified_count > 0:
                        if topup_result:
                            print(f"  [MongoDB] Updated message_id {message_data['message_id']} with topupResult:")
                            print(f"    - Status: {topup_result.get('status', 'N/A')}")
                            if topup_result.get('orderId'):
                                print(f"    - Order ID: #{topup_result['orderId']}")
                            if 'user' in topup_result and topup_result['user']:
                                user_name = topup_result['user'].get('name', 'N/A')
                                user_uid = topup_result['user'].get('uid', 'N/A')
                                print(f"    - User: {user_name} (UID: {user_uid})")
                            if 'payment' in topup_result and topup_result['payment']:
                                payment = topup_result['payment']
                                if payment.get('total'):
                                    print(f"    - Total: {payment['total']}৳")
                                if 'usedUc' in payment:
                                    used_uc = payment['usedUc']
                                    if isinstance(used_uc, dict) and 'codes' in used_uc:
                                        print(f"    - UC Cards: {len(used_uc['codes'])}")
                                    elif isinstance(used_uc, list):
                                        print(f"    - UC Cards: {len(used_uc)}")
                        
                        if account_status:
                            print(f"  [MongoDB] Updated message_id {message_data['message_id']} with account_status:")
                            print(f"    - Name: {account_status['user']['name']}")
                            if 'due' in account_status.get('wallet', {}):
                                print(f"    - Due: {account_status['wallet']['due']}")
                            if 'balance' in account_status.get('wallet', {}):
                                print(f"    - Balance: {account_status['wallet']['balance']}")
                            if 'dueLimit' in account_status.get('wallet', {}):
                                print(f"    - Due Limit: {account_status['wallet']['dueLimit']}")
                        
                        if price_list:
                            uc_count = len(price_list.get("ucPriceList", []))
                            pkg_count = len(price_list.get("specialPackages", []))
                            print(f"  [MongoDB] Updated message_id {message_data['message_id']} with price_list:")
                            print(f"    - UC Prices: {uc_count}")
                            print(f"    - Special Packages: {pkg_count}")
                    
                    return [existing.get("_id")]
                else:
                    print(f"  [MongoDB] Message already exists, no update needed")
                    return None
            
            # Create new document
            document = {
                "message_id": message_data["message_id"],
                "date": message_data["date"],
                "text": message_text,  # Will be None if structured data exists, otherwise cleaned text without emojis (except 🆄🅲)
                "sender_id": message_data["sender_id"],
                "chat_id": message_data["chat_id"],
                "message_type": message_data["message_type"],
                "media_type": message_data.get("media_type"),
                "raw_date": message_data["raw_date"]
            }
            
            # Add topup result if found
            if topup_result:
                document["topupResult"] = topup_result
                print(f"  [MongoDB] Saving topupResult:")
                print(f"    - Status: {topup_result.get('status', 'N/A')}")
                if topup_result.get('orderId'):
                    print(f"    - Order ID: #{topup_result['orderId']}")
                if 'user' in topup_result and topup_result['user']:
                    user_name = topup_result['user'].get('name', 'N/A')
                    user_uid = topup_result['user'].get('uid', 'N/A')
                    print(f"    - User: {user_name} (UID: {user_uid})")
                if 'payment' in topup_result and topup_result['payment']:
                    payment = topup_result['payment']
                    if payment.get('total'):
                        print(f"    - Total: {payment['total']}৳")
                    if 'usedUc' in payment:
                        used_uc = payment['usedUc']
                        if isinstance(used_uc, dict) and 'codes' in used_uc:
                            print(f"    - UC Cards: {len(used_uc['codes'])}")
                        elif isinstance(used_uc, list):
                            print(f"    - UC Cards: {len(used_uc)}")
                if 'meta' in topup_result and topup_result['meta']:
                    if topup_result['meta'].get('durationSec'):
                        print(f"    - Duration: {topup_result['meta']['durationSec']}s")
            
            # Add account status if found
            if account_status:
                document["account_status"] = account_status
                print(f"  [MongoDB] Saving account_status:")
                print(f"    - Name: {account_status['user']['name']}")
                if 'due' in account_status.get('wallet', {}):
                    print(f"    - Due: {account_status['wallet']['due']}")
                if 'balance' in account_status.get('wallet', {}):
                    print(f"    - Balance: {account_status['wallet']['balance']}")
                if 'dueLimit' in account_status.get('wallet', {}):
                    print(f"    - Due Limit: {account_status['wallet']['dueLimit']}")
            
            # Add price list if found
            if price_list:
                document["price_list"] = price_list
                uc_count = len(price_list.get("ucPriceList", []))
                pkg_count = len(price_list.get("specialPackages", []))
                print(f"  [MongoDB] Saving price_list:")
                print(f"    - UC Prices: {uc_count}")
                print(f"    - Special Packages: {pkg_count}")
            
            # Insert into MongoDB
            result = self.mongo_collection.insert_one(document)
            print(f"  [MongoDB] Saved message_id {message_data['message_id']} to MongoDB")
            
            return [result.inserted_id]
            
        except Exception as e:
            print(f"  [MongoDB] ERROR saving: {e}")
            import traceback
            traceback.print_exc()
            return None


    def format_topup_message(self, topup_result):
        """Format TOPUP DONE message for console output."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        output = []
        output.append(f"[{timestamp}] Bot: ✅ TOPUP DONE")
        output.append(f"  Order ID: #{topup_result.get('orderId', 'N/A')}")
        output.append(f"  User: {topup_result.get('user', {}).get('name', 'N/A')} (UID: {topup_result.get('user', {}).get('uid', 'N/A')})")
        
        payment = topup_result.get('payment', {})
        if payment.get('total'):
            output.append(f"  Total: {payment['total']}৳")
        if payment.get('feePerUnit'):
            output.append(f"  Fee/Unit: {payment['feePerUnit']}৳")
        if payment.get('usedUc'):
            # usedUc is now an object with 'codes' array
            used_uc_obj = payment['usedUc']
            if isinstance(used_uc_obj, dict) and 'codes' in used_uc_obj:
                uc_codes = used_uc_obj['codes']
                output.append(f"  UC Cards Used: {len(uc_codes)}")
                for i, card_obj in enumerate(uc_codes[:3], 1):  # Show first 3 cards
                    card_code = card_obj.get('code', 'N/A') if isinstance(card_obj, dict) else str(card_obj)
                    output.append(f"    {i}. {card_code}")
                if len(uc_codes) > 3:
                    output.append(f"    ... and {len(uc_codes) - 3} more")
            elif isinstance(used_uc_obj, list):
                # Fallback for old format (direct array)
                output.append(f"  UC Cards Used: {len(used_uc_obj)}")
                for i, card in enumerate(used_uc_obj[:3], 1):  # Show first 3 cards
                    card_code = card.get('code', 'N/A') if isinstance(card, dict) else str(card)
                    output.append(f"    {i}. {card_code}")
                if len(used_uc_obj) > 3:
                    output.append(f"    ... and {len(used_uc_obj) - 3} more")
        
        product = topup_result.get('product', {})
        if product.get('quantity'):
            output.append(f"  Quantity: {product['quantity']}x")
        if product.get('unitPrice'):
            output.append(f"  Unit Price: {product['unitPrice']}৳")
        
        if payment.get('due') is not None:
            output.append(f"  Due: {payment['due']}৳")
        if payment.get('paid') is not None:
            output.append(f"  Paid: {payment['paid']}৳")
        
        meta = topup_result.get('meta', {})
        if meta.get('durationSec'):
            output.append(f"  Duration: {meta['durationSec']}s")
        
        return "\n".join(output)

    async def message_handler(self, event):
        """Handle incoming messages from the bot."""
        message = event.message
        
        # Extract message data
        message_data = self.extract_message_data(message)
        
        # Check if this is a TOPUP DONE message and format accordingly
        message_text = message.text if message.text else ""
        if message_text:
            # Try to parse topup result for console output
            cleaned_text = self.remove_emojis_except_uc(message_text)
            topup_result = self.parse_topup_result(cleaned_text)
            
            # Store parsed topup_result in message_data for MongoDB saving
            if topup_result:
                message_data["_parsed_topup_result"] = topup_result
                # Print formatted TOPUP DONE message
                formatted_msg = self.format_topup_message(topup_result)
                print(formatted_msg)
            else:
                # Print regular message
                formatted_msg = self.format_message(message)
                print(formatted_msg)
        else:
            # Print regular message for non-text messages
            formatted_msg = self.format_message(message)
            print(formatted_msg)
        
        # Save to MongoDB (all text in one document)
        inserted_ids = self.save_to_mongodb(message_data)
        if inserted_ids:
            print(f"✓ Saved to MongoDB")
        
        # Store response for API access (store last 100 responses)
        async with self.response_lock:
            response_id = f"{message.id}_{datetime.now().timestamp()}"
            self.recent_responses[response_id] = {
                "message_id": message.id,
                "text": message_text,
                "date": message_data["date"],
                "raw_data": message_data
            }
            # Keep only last 100 responses
            if len(self.recent_responses) > 100:
                # Remove oldest response
                oldest_key = min(self.recent_responses.keys(), 
                               key=lambda k: self.recent_responses[k]["date"])
                del self.recent_responses[oldest_key]
        
        print("-" * 80)  # Separator line

    async def send_message_to_bot(self, message_text):
        """Send a message to the bot."""
        try:
            if self.bot_entity is None:
                print("Error: Bot entity not found. Please initialize first.")
                return False
            
            print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Sending to @{self.bot_username}: {message_text}")
            sent_message = await self.client.send_message(self.bot_entity, message_text)
            print(f"✓ Message sent successfully! (Message ID: {sent_message.id})")
            return True
        except Exception as e:
            print(f"✗ Error sending message: {e}")
            return False

    async def start_listening(self):
        """Start listening to bot messages."""
        print(f"\n{'='*80}")
        print(f"Listening to messages from @{self.bot_username}")
        print(f"Send commands to the bot from your Telegram app to see responses here.")
        if self.mongo_collection is not None:
            print(f"Messages will be saved to MongoDB: {config.MONGODB_DATABASE}.{config.MONGODB_COLLECTION}")
        else:
            print(f"Warning: MongoDB not connected. Messages will only be printed to console.")
        print(f"Press Ctrl+C to stop.")
        print(f"{'='*80}\n")
        
        # Register event handler for new messages from the bot
        @self.client.on(events.NewMessage(from_users=self.bot_entity))
        async def handler(event):
            await self.message_handler(event)
        
        # Keep the script running
        await self.client.run_until_disconnected()

    async def run(self, send_message=None):
        """Main run method.
        
        Args:
            send_message: Optional message text to send to the bot immediately after initialization.
        """
        try:
            await self.initialize()
            
            # Send message if provided
            if send_message:
                await self.send_message_to_bot(send_message)
            
            await self.start_listening()
        except KeyboardInterrupt:
            print("\n\nStopping listener...")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            await self.client.disconnect()
            if self.mongo_client:
                self.mongo_client.close()
                print("Disconnected from MongoDB.")
            print("Disconnected from Telegram.")


async def main():
    """Main entry point."""
    import sys
    
    listener = TelegramBotListener()
    
    # Check if message is provided as command line argument
    message_to_send = None
    if len(sys.argv) > 1:
        message_to_send = " ".join(sys.argv[1:])
        print(f"Message to send: {message_to_send}")
    
    await listener.run(send_message=message_to_send)


if __name__ == "__main__":
    asyncio.run(main())