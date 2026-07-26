# REQUIRES: requests, brotli, telethon

import requests
import time
import random
import sys
import json
import os
import brotli
import asyncio
import urllib.parse
import logging
from datetime import datetime
from telethon import TelegramClient, functions
from telethon.errors import SessionPasswordNeededError

# ==========================================
# DISABLE TELEPHON LOGGING
# ==========================================
logging.getLogger('telethon').setLevel(logging.ERROR)
logging.getLogger('asyncio').setLevel(logging.ERROR)

# ==========================================
# CONFIG
# ==========================================
API_ID = 35872666
API_HASH = "17525975ad234af56f886abedc69a4d9"
BOT_USERNAME = "litebits_faucet_bot"
AUTH_URL = "https://mini.litebits.io/api/auth/telegram/validate"
BASE_URL = "https://mini.litebits.io"
SESSION_FILE = "session.txt"
COOKIE = "bitmedia_fid=eyJmaWQiOiIzMTUyY2M0ZjcxYjZkZmY0NzJjMzQzZDIxOTIzMmFhMiIsImZpZG5vdWEiOiJhM2Q4YzY0YWM5Y2VjYzRjMWI0N2Y0MDY2MzVjZGVjMyJ9"

# ==========================================
# TOKEN EXTRACTOR
# ==========================================
async def get_bearer_token():
    """Get bearer token using Telethon"""
    client = None
    
    try:
        # Try to load existing session
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, 'r') as f:
                phone = f.read().strip()
        else:
            phone = input("📱 Enter phone number: ").strip()
            if not phone:
                print("❌ Phone required!")
                return None
            with open(SESSION_FILE, 'w') as f:
                f.write(phone)
        
        # Connect to Telegram (silent)
        client = TelegramClient(f"session_{phone.replace('+', '')}", API_ID, API_HASH)
        await client.connect()
        
        # Login if needed (silent)
        if not await client.is_user_authorized():
            await client.send_code_request(phone)
            code = input("📨 Enter OTP: ").strip()
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                password = input("🔑 Enter 2FA: ").strip()
                await client.sign_in(password=password)
        
        # Get bot webview
        bot = await client.get_input_entity(BOT_USERNAME)
        result = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform='android',
            from_bot_menu=True,
            url='https://mini.litebits.io/'
        ))
        
        # Extract initData
        parsed = urllib.parse.urlparse(result.url)
        fragment = parsed.fragment or parsed.query
        query = urllib.parse.parse_qs(fragment)
        init_data = query.get('tgWebAppData', [None])[0]
        
        if not init_data:
            print("❌ Failed to get initData")
            return None
        
        # Exchange for bearer token
        headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://mini.litebits.io",
            "referer": "https://mini.litebits.io/?v5",
            "x-platform": "telegram",
            "user-agent": "Mozilla/5.0 (Linux; Android 14; K) AppleWebKit/537.36"
        }
        
        res = requests.post(AUTH_URL, json={"initData": init_data}, headers=headers, timeout=15)
        
        if res.status_code in [200, 201]:
            data = res.json()
            token = data.get("token") or data.get("accessToken") or data.get("data", {}).get("token")
            if token:
                return token.replace("Bearer ", "").strip()
        
        print("❌ Failed to get token")
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None
    finally:
        if client:
            await client.disconnect()

# ==========================================
# CLAIM BOT
# ==========================================
class LiteBitsBot:
    def __init__(self, token):
        self.token = token
        self.balance = 0.0
        self.headers = {
            "host": "mini.litebits.io",
            "x-platform": "telegram",
            "authorization": f"Bearer {token}",
            "sec-ch-ua-platform": '"Android"',
            "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Android WebView";v="150"',
            "sec-ch-ua-mobile": "?0",
            "user-agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.46 Safari/537.36 Telegram-Android/12.6.4 (Samsung SM-X110; Android 16; SDK 36; AVERAGE)",
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json",
            "origin": "https://mini.litebits.io",
            "x-requested-with": "org.telegram.messenger.web",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": "https://mini.litebits.io/?v5",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-IN,en-US;q=0.9,en;q=0.8",
            "cookie": COOKIE,
            "priority": "u=1, i"
        }
    
    def get_profile(self):
        try:
            headers = {
                "host": "mini.litebits.io",
                "x-platform": "telegram",
                "authorization": f"Bearer {self.token}",
                "sec-ch-ua-platform": '"Android"',
                "user-agent": "Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.46 Safari/537.36 Telegram-Android/12.6.4",
                "accept": "application/json, text/plain, */*",
                "sec-ch-ua": '"Not;A=Brand";v="8", "Chromium";v="150", "Android WebView";v="150"',
                "sec-ch-ua-mobile": "?0",
                "x-requested-with": "org.telegram.messenger.web",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://mini.litebits.io/?v5",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-IN,en-US;q=0.9,en;q=0.8",
                "cookie": COOKIE,
                "priority": "u=1, i"
            }
            
            r = requests.get(f"{BASE_URL}/api/user/profile", headers=headers)
            
            if r.status_code == 200:
                content_encoding = r.headers.get('content-encoding', '')
                
                if 'br' in content_encoding:
                    try:
                        decoded = brotli.decompress(r.content)
                        data = json.loads(decoded.decode('utf-8'))
                    except:
                        data = r.json()
                else:
                    data = r.json()
                
                if data.get('balance'):
                    self.balance = float(data['balance'])
                    return True
            return False
        except:
            return False
    
    def wait(self, seconds):
        for i in range(int(seconds), 0, -1):
            print(f"⏳ {i}s remaining", end='\r')
            time.sleep(1)
        print(" " * 20, end='\r')
    
    def claim(self):
        r = requests.post(f"{BASE_URL}/api/claim/start", headers=self.headers, 
                         json={"h-captcha-response": "", "captchaProvider": "hcaptcha", "tapTimings": [], "fingerprint": ""})
        if r.status_code != 200:
            return None
        
        data = r.json()
        if not data.get('success'):
            if 'existingClaimId' in data:
                claim_id = data['existingClaimId']
            else:
                return None
        else:
            claim_id = data['claimId']
        
        time.sleep(random.uniform(0.5, 1.0))
        
        r = requests.get(f"{BASE_URL}/api/claim/{claim_id}/ads", headers=self.headers)
        if r.status_code != 200:
            return None
        
        data = r.json()
        if not data.get('success'):
            return None
        
        token = data.get('adsUrl', {}).get('token')
        if not token:
            return None
        
        wait = random.uniform(10, 13)
        print(f"📺 Watching ad...")
        self.wait(wait)
        
        r = requests.post(f"{BASE_URL}/api/claim/{claim_id}/complete", 
                         headers=self.headers, json={"token": token})
        
        if r.status_code != 200:
            return None
        
        data = r.json()
        if data.get('success'):
            return data.get('reward')
        return None
    
    def run(self):
        print("\n" + "=" * 40)
        print("💰 LiteBits Bot Running")
        if self.get_profile():
            print(f"💳 Balance: {self.balance:.2f} sats")
        print("Press Ctrl+C to stop")
        print("=" * 40 + "\n")
        
        count = 0
        earned = 0
        
        while True:
            try:
                reward = self.claim()
                
                if reward:
                    count += 1
                    earned += reward
                    self.balance += reward
                    print(f"✅ #{count} | +{reward} sats | Balance: {self.balance:.2f} sats")
                else:
                    print(f"❌ Claim #{count + 1} failed")
                
                minutes = random.uniform(6, 9)
                print(f"\n⏰ Next claim in {minutes:.1f} minutes")
                self.wait(int(minutes * 60))
                print()
                
            except KeyboardInterrupt:
                print(f"\n\n🛑 Stopped | Claims: {count} | Earned: {earned:.2f} sats")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                time.sleep(60)

# ==========================================
# MAIN
# ==========================================
async def main():
    print("\n" + "=" * 40)
    print("💰 LiteBits Auto Bot")
    print("=" * 40 + "\n")
    
    token = await get_bearer_token()
    if not token:
        print("❌ Failed to get token!")
        return
    
    bot = LiteBitsBot(token)
    bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Stopped")
        sys.exit(0)
