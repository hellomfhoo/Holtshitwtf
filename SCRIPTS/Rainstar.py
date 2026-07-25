

import asyncio
import urllib.parse
import requests
import json
import time
import random
import re
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from telethon import TelegramClient, functions, types

# ============================================
# CONFIGURATION
# ============================================
API_HASH = 'fb06985ea797ac51aaa1e6d1168ceaaa'
API_ID = '35898257'
BOT_USERNAME = 'Rain_starbot'
BASE_URL = "https://rainstar.online"
MAX_ADS = 20  # HARDCODED AD LIMIT

# ============================================
# CLEAR SCREEN
# ============================================
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

# ============================================
# RAINSTAR BOT
# ============================================
class RainStarBot:
    def __init__(self, init_data: str):
        self.base_url = BASE_URL
        self.init_data = init_data
        self.device_id = None
        self.session = requests.Session()
        
        self.base_headers = {
            'Host': 'rainstar.online',
            'Content-Type': 'application/json',
            'x-telegram-init-data': self.init_data,
            'x-device-id': '',
            'x-requested-with': 'org.telegram.messenger.web',
            'Origin': 'https://rainstar.online',
            'Referer': f'https://rainstar.online/?tgWebAppStartParam=8597801059',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 16; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.7871.124 Safari/537.36 Telegram-Android/12.6.4 (Samsung SM-X110; Android 16; SDK 36; AVERAGE)',
            'Accept': '*/*',
            'Accept-Language': 'en-IN,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Sec-Ch-Ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Android WebView";v="150"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Android"',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Dest': 'empty',
            'Priority': 'u=1, i'
        }
        
        self.responses = {}
        self.last_ad_time = 0
        self.last_game_time = 0
        
        self.limits = {
            'spinTickets': 0,
            'diceToday': 0,
            'maxDice': 20,
            'adsToday': 0,
            'adsgramToday': 0,
            'monetagToday': 0,
            'adexiumToday': 0,
            'dailyStreak': 0,
            'miningStatus': 'idle',
            'firstName': 'Player'
        }
        
        self.stats = {
            'ads_watched': 0,
            'ads_reward': 0,
            'spins_done': 0,
            'spins_reward': 0,
            'dice_rolled': 0,
            'dice_reward': 0,
            'mining_reward': 0
        }
        
        self.start_balance = 0
        self.current_balance = 0
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, label: str = "", skip_errors: bool = False) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        headers = self.base_headers.copy()
        
        if self.device_id:
            headers['x-device-id'] = self.device_id
        
        if data:
            headers['Content-Length'] = str(len(json.dumps(data)))
        
        try:
            if data:
                print(f"  → {json.dumps(data)}")
            
            start_time = time.time()
            
            if method.upper() == 'GET':
                response = self.session.get(url, headers=headers, timeout=30)
            else:
                response = self.session.post(url, headers=headers, json=data, timeout=30)
            
            elapsed = time.time() - start_time
            
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                response_data = {"raw": response.text}
            
            self.responses[endpoint] = {
                'timestamp': datetime.now().isoformat(),
                'status': response.status_code,
                'data': response_data,
                'elapsed': elapsed
            }
            
            if response.status_code >= 400 or response_data.get('error'):
                error_msg = response_data.get('error', f"HTTP {response.status_code}")
                
                wait_match = re.search(r'wait (\d+)s?', error_msg.lower())
                if wait_match:
                    wait_time = int(wait_match.group(1))
                    print(f"  ⏳ Wait {wait_time}s...")
                    time.sleep(wait_time + 2)
                
                if any(x in error_msg.lower() for x in ["already claimed", "already in progress", "please wait", "still in progress"]):
                    print(f"  ⏭️  {error_msg}")
                    return response_data
                
                if skip_errors:
                    return response_data
                
                raise Exception(f"Error: {error_msg}")
            
            if 'reward' in response_data and response_data.get('reward', 0) > 0:
                reward = response_data.get('reward', 0)
                
                if 'balance' in response_data:
                    self.current_balance = response_data.get('balance', self.current_balance)
                
                if 'spin' in label.lower():
                    self.stats['spins_reward'] += reward
                    self.last_game_time = time.time()
                elif 'dice' in label.lower():
                    self.stats['dice_reward'] += reward
                    self.last_game_time = time.time()
                elif 'ad-watch' in endpoint.lower():
                    self.stats['ads_reward'] += reward
                    self.last_ad_time = time.time()
                    self.stats['ads_watched'] += 1
                elif 'claim' in endpoint.lower():
                    self.stats['mining_reward'] += reward
                
                print(f"  ⭐ {self.current_balance:,}")
            
            if 'user' in response_data and 'balance' in response_data['user']:
                self.current_balance = response_data['user'].get('balance', self.current_balance)
                self._update_limits(response_data)
            
            return response_data
            
        except Exception as e:
            print(f"  ❌ {str(e)}")
            raise
    
    def _update_limits(self, response_data: Dict):
        user = response_data.get('user', {})
        if user:
            self.limits['spinTickets'] = user.get('spinTickets', 0)
            self.limits['diceToday'] = user.get('diceToday', 0)
            self.limits['maxDice'] = user.get('maxDice', 20)
            self.limits['adsToday'] = user.get('adsToday', 0)
            self.limits['adsgramToday'] = user.get('adsgramToday', 0)
            self.limits['monetagToday'] = user.get('monetagToday', 0)
            self.limits['adexiumToday'] = user.get('adexiumToday', 0)
            self.limits['dailyStreak'] = user.get('dailyStreak', 0)
            self.limits['firstName'] = user.get('firstName', 'Player')
            
            mining = user.get('mining', {})
            if mining:
                self.limits['miningStatus'] = mining.get('status', 'idle')
            
            self.current_balance = user.get('balance', self.current_balance)
    
    def _fetch_user(self):
        result = self._make_request('GET', '/api/user', label="user")
        if result and 'user' in result:
            device_id = result['user'].get('deviceId')
            if device_id:
                self.device_id = device_id
            self._update_limits(result)
            self.current_balance = result['user'].get('balance', 0)
        return result
    
    def _claim_daily(self):
        self._make_request('POST', '/api/user/daily-claim', label="daily", skip_errors=True)
    
    def _start_mining(self):
        if self.limits.get('miningStatus') == 'mining':
            return
        self._make_request('POST', '/api/user/mining/start', label="mining", skip_errors=True)
    
    def _ad_start(self):
        self._make_request('POST', '/api/user/ad-start', label="ad_start")
    
    def _ad_watch(self, provider: str = "adsgram"):
        result = self._make_request('POST', '/api/user/ad-watch', {'provider': provider}, label="ad_watch", skip_errors=True)
        return result
    
    def _spin(self):
        result = self._make_request('POST', '/api/user/spin', label="spin", skip_errors=True)
        if result and 'reward' in result:
            self.stats['spins_done'] += 1
        return result
    
    def _dice(self):
        result = self._make_request('POST', '/api/user/dice', label="dice", skip_errors=True)
        if result and 'reward' in result:
            self.stats['dice_rolled'] += 1
        return result
    
    def _claim_mining(self):
        if self.limits.get('miningStatus') == 'idle':
            return
        self._make_request('POST', '/api/user/mining/claim', label="claim", skip_errors=True)
    
    def _can_spin(self):
        return self.limits.get('spinTickets', 0) > 0
    
    def _can_dice(self):
        return self.limits.get('diceToday', 0) < self.limits.get('maxDice', 20)
    
    def _wait(self, last_time: float, min_wait: int = 5, label: str = ""):
        elapsed = time.time() - last_time
        if elapsed < min_wait:
            wait = min_wait - elapsed
            if label:
                print(f"  ⏳ {label} {wait:.0f}s...")
            else:
                print(f"  ⏳ {wait:.0f}s...")
            time.sleep(wait)
    
    def _show_progress(self):
        print(f"\n{'─'*40}")
        print(f"⭐ {self.current_balance:,}  |  📺 {self.stats['ads_watched']}/{MAX_ADS}  |  🎫 {self.stats['spins_done']}  |  🎲 {self.stats['dice_rolled']}/{self.limits.get('maxDice', 20)}")
        print(f"{'─'*40}")
    
    def run(self):
        print("\n" + "█"*40)
        print("🚀 RAINSTAR BOT")
        print("█"*40)
        
        try:
            print("\n📊 Loading profile...")
            self._fetch_user()
            self.start_balance = self.current_balance
            
            name = self.limits.get('firstName', 'Player')
            print(f"  👤 {name}")
            print(f"  ⭐ {self.current_balance:,}")
            print(f"  📺 Today: {self.limits.get('adsToday', 0)}/{MAX_ADS}")
            
            print("\n🎁 Daily claim...")
            self._claim_daily()
            time.sleep(1)
            
            print("\n⛏️ Starting mining...")
            self._start_mining()
            time.sleep(1)
            
            print("\n" + "█"*40)
            print("📺 ADS")
            print("█"*40)
            
            ad_count = 0
            max_failures = 5
            failures = 0
            
            while ad_count < MAX_ADS:
                self._wait(self.last_ad_time, 8, "Ad")
                self._ad_start()
                print("  ⏳ 15s...")
                time.sleep(15)
                
                providers = ['adsgram', 'monetag', 'adexium']
                success = False
                
                for provider in providers:
                    result = self._ad_watch(provider)
                    if result and result.get('reward', 0) > 0:
                        success = True
                        ad_count += 1
                        break
                    elif result and 'error' in result:
                        if 'please wait' in result.get('error', '').lower():
                            continue
                
                if not success:
                    failures += 1
                    if failures >= max_failures:
                        print(f"\n⚠️ Too many failures ({failures}), stopping ads")
                        break
                    print(f"  ⚠️ Failed ({failures}/{max_failures}), waiting 10s...")
                    time.sleep(10)
                    continue
                else:
                    failures = 0
                
                self._show_progress()
                delay = random.uniform(4, 8)
                print(f"  ⏳ {delay:.0f}s...")
                time.sleep(delay)
            
            print(f"\n✅ {ad_count}/{MAX_ADS} ads done")
            
            print("\n" + "█"*40)
            print("🎮 GAMES")
            print("█"*40)
            
            time.sleep(3)
            cycle = 0
            
            while True:
                cycle += 1
                print(f"\n▶ {cycle}")
                
                any_played = False
                
                if self._can_spin():
                    self._wait(self.last_game_time, 4, "Game")
                    self._spin()
                    any_played = True
                    time.sleep(random.uniform(1, 3))
                
                if self._can_dice():
                    self._wait(self.last_game_time, 3, "Game")
                    self._dice()
                    any_played = True
                    time.sleep(random.uniform(1, 3))
                
                self._show_progress()
                
                if not self._can_spin() and not self._can_dice():
                    print("\n✅ All games done!")
                    break
                
                if not any_played:
                    print("  ⏳ Refreshing...")
                    self._fetch_user()
                    time.sleep(5)
                    continue
                
                delay = random.uniform(3, 6)
                print(f"  ⏳ {delay:.0f}s...")
                time.sleep(delay)
            
            time.sleep(2)
            print("\n" + "█"*40)
            print("💎 CLAIM")
            print("█"*40)
            self._claim_mining()
            
            self._fetch_user()
            total = self.current_balance - self.start_balance
            
            print("\n" + "█"*40)
            print("✅ SUMMARY")
            print("█"*40)
            print(f"\n  Start:  {self.start_balance:,} ⭐")
            print(f"  End:    {self.current_balance:,} ⭐")
            print(f"  Earned: {total:,} ⭐")
            print(f"\n  📺 Ads:   +{self.stats['ads_reward']:,} ⭐ ({self.stats['ads_watched']}/{MAX_ADS})")
            print(f"  🎡 Spin:  +{self.stats['spins_reward']:,} ⭐ ({self.stats['spins_done']})")
            print(f"  🎲 Dice:  +{self.stats['dice_reward']:,} ⭐ ({self.stats['dice_rolled']})")
            print(f"  💎 Mine:  +{self.stats['mining_reward']:,} ⭐")
            print("\n" + "█"*40)
            print("✅ DONE")
            print("█"*40)
            
            return {
                'start': self.start_balance,
                'end': self.current_balance,
                'earned': total,
                'stats': self.stats
            }
            
        except KeyboardInterrupt:
            print("\n\n⚠️ Stopped")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ {str(e)}")
            raise

# ============================================
# AUTO EXTRACT INIT DATA
# ============================================
async def extract_init_data():
    """Auto extract init data from Telegram bot"""
    client = TelegramClient('session_auth', API_ID, API_HASH)
    
    print("\n🔐 Logging into Telegram...")
    await client.start()
    print("✅ Logged in!")
    
    try:
        print(f"📡 Getting bot @{BOT_USERNAME}...")
        bot = await client.get_input_entity(BOT_USERNAME)
        
        print("📡 Getting webview...")
        result = await client(functions.messages.RequestWebViewRequest(
            peer=bot,
            bot=bot,
            platform='android',
            from_bot_menu=True,
            url='https://rainstar.online/'
        ))

        parsed_url = urllib.parse.urlparse(result.url)
        fragment = parsed_url.fragment
        query_params = urllib.parse.parse_qs(fragment)
        init_data = query_params.get('tgWebAppData', [None])[0]

        if init_data:
            with open("init_data.txt", "w") as f:
                f.write(init_data)
            await client.disconnect()
            return init_data
        else:
            await client.disconnect()
            return None

    except Exception as e:
        print(f"❌ Error: {e}")
        await client.disconnect()
        return None

# ============================================
# MAIN - AUTO LOGIN & RUN
# ============================================
def main():
    clear()
    print("\n" + "█"*50)
    print("🚀 RAINSTAR BOT - AUTO LOGIN")
    print("█"*50)
    
    print("\n📡 Auto-extracting init data from Telegram...")
    
    init_data = asyncio.run(extract_init_data())
    
    if not init_data:
        print("\n❌ Failed to extract init data!")
        print("   Trying to read from saved file...")
        try:
            with open("init_data.txt", "r") as f:
                init_data = f.read().strip()
            print("✅ Loaded from init_data.txt")
        except:
            print("\n❌ No init data found.")
            sys.exit(1)
    
    if init_data:
        print("✅ Init data extracted!")
        clear()
        
        print("\n" + "█"*50)
        print("🚀 RAINSTAR BOT RUNNING")
        print("█"*50)
        
        bot = RainStarBot(init_data)
        
        try:
            results = bot.run()
            
            with open("api_responses.json", "w") as f:
                json.dump(bot.responses, f, indent=2, default=str)
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Stopped")
        sys.exit(0)
