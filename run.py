import requests
import json
import time
import random
import sys
import os
from datetime import datetime
from fake_useragent import UserAgent
from colorama import init, Fore, Style

init(autoreset=True)

class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.load_proxies()
    
    def load_proxies(self):
        try:
            if os.path.exists('proxy.txt'):
                with open('proxy.txt', 'r') as f:
                    self.proxies = [line.strip() for line in f if line.strip()]
                print(f"{Fore.GREEN}✅ Loaded {len(self.proxies)} proxies")
            else:
                print(f"{Fore.YELLOW}⚠️  proxy.txt not found, running without proxy")
        except Exception as e:
            print(f"{Fore.RED}❌ Error loading proxies: {str(e)}")
    
    def get_proxy(self):
        if not self.proxies:
            return None
        return random.choice(self.proxies)

class AccountManager:
    def __init__(self):
        self.accounts = []
        self.load_accounts()
    
    def load_accounts(self):
        try:
            if os.path.exists('akun.json'):
                with open('akun.json', 'r') as f:
                    self.accounts = json.load(f)
                print(f"{Fore.GREEN}✅ Loaded {len(self.accounts)} accounts")
            else:
                print(f"{Fore.RED}❌ akun.json not found!")
                sys.exit(1)
        except Exception as e:
            print(f"{Fore.RED}❌ Error loading accounts: {str(e)}")
            sys.exit(1)
    
    def get_account(self, index=None):
        if not self.accounts:
            return None
        if index is None:
            return random.choice(self.accounts)
        return self.accounts[index % len(self.accounts)]

class TransferBot:
    def __init__(self):
        self.base_url = "https://campapi.diamante.io/api/v1/transaction/transfer"
        self.account_manager = AccountManager()
        self.proxy_manager = ProxyManager()
        self.ua = UserAgent()
        self.setup_logging()
        self.stats = {
            'total_transfers': 0,
            'successful': 0,
            'failed': 0,
            'retries': 0
        }
    
    def setup_logging(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = f"logs/transfer_{timestamp}.txt"
        
        if not os.path.exists('logs'):
            os.makedirs('logs')
    
    def log(self, message, account_nick=None, color=Fore.WHITE):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prefix = f"[{account_nick}] " if account_nick else ""
        log_line = f"[{timestamp}] {prefix}{message}"
        
        print(f"{color}{log_line}")
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line.replace('\033[', '[') + '\n')
    
    def read_addresses(self):
        try:
            with open('adrs.txt', 'r') as f:
                addresses = [line.strip() for line in f if line.strip()]
            
            valid_addresses = []
            for addr in addresses:
                if addr.startswith('0x') and len(addr) == 42:
                    valid_addresses.append(addr)
                else:
                    self.log(f"Invalid address: {addr}", color=Fore.YELLOW)
            
            return valid_addresses
        except FileNotFoundError:
            self.log("adrs.txt not found!", color=Fore.RED)
            return []
    
    def create_headers(self, account):
        user_agent = self.ua.random
        
        return {
            'authority': 'campapi.diamante.io',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.6',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'access-token': 'key',
            'content-type': 'application/json',
            'cookie': account['cookie'],
            'origin': 'https://campaign.diamante.io',
            'priority': 'u=1, i',
            'referer': 'https://campaign.diamante.io/',
            'sec-ch-ua': '"Brave";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'sec-gpc': '1',
            'user-agent': user_agent
        }
    
    def create_payload(self, to_address, amount, account):
        return {
            "toAddress": to_address,
            "amount": amount,
            "userId": account['user_id']
        }
    
    def transfer_with_retry(self, to_address, amount, account, max_retries=10):
        retry_count = 0
        account_nick = account.get('nickname', 'Unknown')
        
        while retry_count < max_retries:
            retry_count += 1
            self.stats['retries'] += 1
            
            if retry_count > 1:
                retry_delay = random.randint(10, 30)
                self.log(f"Retry {retry_count}/{max_retries}", account_nick, Fore.YELLOW)
                self.log(f"Delay {retry_delay}s", account_nick, Fore.YELLOW)
                time.sleep(retry_delay)
            
            try:
                payload = self.create_payload(to_address, amount, account)
                headers = self.create_headers(account)
                
                proxy = self.proxy_manager.get_proxy()
                proxies = None
                if proxy:
                    proxies = {
                        'http': proxy,
                        'https': proxy
                    }
                
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    proxies=proxies,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        return True, result
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        
                        if any(err in error_msg.lower() for err in ['rate limit', 'database', 'internal', 'timeout', 'busy']):
                            self.log(f"Error: {error_msg} (retry)", account_nick, Fore.YELLOW)
                            continue
                        else:
                            return False, result
                
                elif response.status_code == 429:
                    self.log("Rate limit (429)", account_nick, Fore.YELLOW)
                    wait_time = random.randint(30, 60)
                    self.log(f"Wait {wait_time}s", account_nick, Fore.YELLOW)
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code >= 500:
                    self.log(f"Server error {response.status_code}", account_nick, Fore.YELLOW)
                    continue
                
                else:
                    self.log(f"HTTP {response.status_code}", account_nick, Fore.YELLOW)
                    continue
                    
            except requests.exceptions.Timeout:
                self.log("Timeout (retry)", account_nick, Fore.YELLOW)
                continue
                
            except requests.exceptions.ConnectionError:
                self.log("Connection error (retry)", account_nick, Fore.YELLOW)
                time.sleep(15)
                continue
                
            except Exception as e:
                self.log(f"Exception: {str(e)}", account_nick, Fore.RED)
                continue
        
        return False, {"error": "Max retries"}
    
    def process_transfers(self, mode='round_robin', amount=0.001, min_delay=5, max_delay=15):
        addresses = self.read_addresses()
        if not addresses:
            return
        
        accounts = self.account_manager.accounts
        
        self.log(f"Starting transfer", color=Fore.CYAN)
        self.log(f"Mode: {mode}", color=Fore.CYAN)
        self.log(f"Accounts: {len(accounts)}", color=Fore.CYAN)
        self.log(f"Addresses: {len(addresses)}", color=Fore.CYAN)
        self.log(f"Amount: {amount} ETH", color=Fore.CYAN)
        self.log(f"Delay: {min_delay}-{max_delay}s", color=Fore.CYAN)
        self.log("=" * 60, color=Fore.CYAN)
        
        if mode == 'round_robin':
            total_transfers = len(accounts) * len(addresses)
            current = 0
            
            for account_idx, account in enumerate(accounts):
                account_nick = account.get('nickname', f'Account {account_idx+1}')
                
                for addr_idx, address in enumerate(addresses):
                    current += 1
                    self.stats['total_transfers'] += 1
                    
                    self.log(f"Transfer {current}/{total_transfers}", account_nick, Fore.BLUE)
                    self.log(f"To: {address[:10]}...{address[-6:]}", account_nick, Fore.BLUE)
                    
                    success, result = self.transfer_with_retry(address, amount, account)
                    
                    if success:
                        self.stats['successful'] += 1
                        self.log(f"Success!", account_nick, Fore.GREEN)
                        self.log(f"Hash: {result['data']['transferData']['hash'][:20]}...", account_nick, Fore.GREEN)
                    else:
                        self.stats['failed'] += 1
                        self.log(f"Failed", account_nick, Fore.RED)
                    
                    if not (account_idx == len(accounts)-1 and addr_idx == len(addresses)-1):
                        delay = random.randint(min_delay, max_delay)
                        self.log(f"Wait {delay}s", account_nick, Fore.MAGENTA)
                        time.sleep(delay)
        
        elif mode == 'sequential':
            for idx, address in enumerate(addresses):
                self.stats['total_transfers'] += 1
                account = accounts[idx % len(accounts)]
                account_nick = account.get('nickname', f'Account {idx % len(accounts) + 1}')
                
                self.log(f"Transfer {idx+1}/{len(addresses)}", account_nick, Fore.BLUE)
                self.log(f"To: {address[:10]}...{address[-6:]}", account_nick, Fore.BLUE)
                
                success, result = self.transfer_with_retry(address, amount, account)
                
                if success:
                    self.stats['successful'] += 1
                    self.log(f"Success!", account_nick, Fore.GREEN)
                    self.log(f"Hash: {result['data']['transferData']['hash'][:20]}...", account_nick, Fore.GREEN)
                else:
                    self.stats['failed'] += 1
                    self.log(f"Failed", account_nick, Fore.RED)
                
                if idx < len(addresses) - 1:
                    delay = random.randint(min_delay, max_delay)
                    self.log(f"Wait {delay}s", account_nick, Fore.MAGENTA)
                    time.sleep(delay)
        
        elif mode == 'random':
            for idx, address in enumerate(addresses):
                self.stats['total_transfers'] += 1
                account = self.account_manager.get_account()
                account_nick = account.get('nickname', 'Random')
                
                self.log(f"Transfer {idx+1}/{len(addresses)}", account_nick, Fore.BLUE)
                self.log(f"To: {address[:10]}...{address[-6:]}", account_nick, Fore.BLUE)
                
                success, result = self.transfer_with_retry(address, amount, account)
                
                if success:
                    self.stats['successful'] += 1
                    self.log(f"Success!", account_nick, Fore.GREEN)
                    self.log(f"Hash: {result['data']['transferData']['hash'][:20]}...", account_nick, Fore.GREEN)
                else:
                    self.stats['failed'] += 1
                    self.log(f"Failed", account_nick, Fore.RED)
                
                if idx < len(addresses) - 1:
                    delay = random.randint(min_delay, max_delay)
                    self.log(f"Wait {delay}s", account_nick, Fore.MAGENTA)
                    time.sleep(delay)
        
        self.log("=" * 60, color=Fore.CYAN)
        self.log("📊 TRANSFER SUMMARY", color=Fore.CYAN)
        self.log(f"Total transfers: {self.stats['total_transfers']}", color=Fore.CYAN)
        self.log(f"Successful: {self.stats['successful']}", color=Fore.GREEN)
        self.log(f"Failed: {self.stats['failed']}", color=Fore.RED)
        self.log(f"Total retries: {self.stats['retries']}", color=Fore.YELLOW)
        self.log(f"Success rate: {self.stats['successful']/self.stats['total_transfers']*100:.1f}%", color=Fore.CYAN)

def print_banner():
    banner = f"""
{Fore.CYAN}{'='*60}
{Fore.YELLOW}   ╔═╗╔═╗╔╦╗  ╔╦╗╔═╗╔═╗╔╦╗╔═╗╦═╗╔═╗
{Fore.YELLOW}   ║  ║ ║║║║   ║║╠═╝╠═╣ ║ ║╣ ╠╦╝╚═╗
{Fore.YELLOW}   ╚═╝╚═╝╩ ╩  ═╩╝╩  ╩ ╩ ╩ ╚═╝╩╚═╚═╝
{Fore.CYAN}{'='*60}
{Fore.WHITE}   Auto Transfer Bot v3.0 | Multi-Account | Proxy Support
{Fore.CYAN}{'='*60}
    """
    print(banner)

def main():
    print_banner()
    
    bot = TransferBot()
    
    print(f"\n{Fore.CYAN}⚙️  CONFIGURATION")
    print(f"{Fore.CYAN}{'-'*30}")
    
    while True:
        try:
            amount_input = input(f"{Fore.WHITE}Amount ETH (default 0.001): ").strip()
            amount = float(amount_input) if amount_input else 0.001
            if amount > 0:
                break
            else:
                print(f"{Fore.RED}Amount must be > 0")
        except:
            print(f"{Fore.RED}Invalid amount")
    
    while True:
        try:
            min_delay_input = input(f"{Fore.WHITE}Min delay (seconds, default 5): ").strip()
            min_delay = int(min_delay_input) if min_delay_input else 5
            
            max_delay_input = input(f"{Fore.WHITE}Max delay (seconds, default 15): ").strip()
            max_delay = int(max_delay_input) if max_delay_input else 15
            
            if 0 < min_delay <= max_delay:
                break
            else:
                print(f"{Fore.RED}Invalid delay values")
        except:
            print(f"{Fore.RED}Invalid input")
    
    print(f"\n{Fore.CYAN}🎯 TRANSFER MODE")
    print(f"{Fore.CYAN}{'-'*30}")
    print(f"{Fore.WHITE}1. Round Robin - Each account transfers to all addresses")
    print(f"{Fore.WHITE}2. Sequential - Each address gets one transfer (rotating accounts)")
    print(f"{Fore.WHITE}3. Random - Random account for each address")
    
    while True:
        mode_choice = input(f"\n{Fore.WHITE}Select mode (1/2/3, default 2): ").strip()
        if not mode_choice:
            mode = 'sequential'
            break
        elif mode_choice == '1':
            mode = 'round_robin'
            break
        elif mode_choice == '2':
            mode = 'sequential'
            break
        elif mode_choice == '3':
            mode = 'random'
            break
        else:
            print(f"{Fore.RED}Invalid choice")
    
    while True:
        try:
            retry_input = input(f"{Fore.WHITE}Max retries per transfer (default 10): ").strip()
            max_retries = int(retry_input) if retry_input else 10
            if max_retries >= 1:
                break
            else:
                print(f"{Fore.RED}Must be at least 1")
        except:
            print(f"{Fore.RED}Invalid input")
    
    print(f"\n{Fore.YELLOW}⚠️  CONFIRMATION")
    print(f"{Fore.YELLOW}{'-'*30}")
    print(f"{Fore.WHITE}Mode: {mode}")
    print(f"{Fore.WHITE}Amount: {amount} ETH")
    print(f"{Fore.WHITE}Delay: {min_delay}-{max_delay} seconds")
    print(f"{Fore.WHITE}Max retries: {max_retries}")
    print(f"{Fore.WHITE}Accounts: {len(bot.account_manager.accounts)}")
    print(f"{Fore.WHITE}Proxies: {len(bot.proxy_manager.proxies)}")
    
    confirm = input(f"\n{Fore.GREEN}Start transfer? (y/n): ").lower()
    if confirm != 'y':
        print(f"{Fore.YELLOW}Transfer cancelled")
        return
    
    print(f"\n{Fore.GREEN}🚀 Starting transfer...")
    print(f"{Fore.GREEN}📁 Log file: {bot.log_file}")
    
    try:
        bot.process_transfers(mode, amount, min_delay, max_delay)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}⚠️  Transfer interrupted by user")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Error: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}👋 Exiting...")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Fatal error: {str(e)}")
