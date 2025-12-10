import requests
import json
import time
import random
import sys
from datetime import datetime

class TransferBot:
    def __init__(self):
        self.base_url = "https://campapi.diamante.io/api/v1/transaction/transfer"
        self.load_config()
        self.setup_logging()
        
    def load_config(self):
        try:
            with open('akun.txt', 'r') as f:
                lines = f.readlines()
            
            config = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
            
            self.cookie = config.get('cookie', '')
            self.user_id = config.get('user_id', '')
            self.default_amount = float(config.get('amount', 0.001))
            
            if not self.cookie or not self.user_id:
                sys.exit("Error: Data akun.txt tidak lengkap")
                
        except FileNotFoundError:
            sys.exit("Error: File akun.txt tidak ditemukan")
        except Exception as e:
            sys.exit(f"Error: Gagal membaca akun.txt - {str(e)}")
    
    def setup_logging(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = f"transfer_log_{timestamp}.txt"
    
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] {message}"
        print(log_line)
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')
    
    def read_addresses(self):
        try:
            with open('adrs.txt', 'r') as f:
                addresses = [line.strip() for line in f if line.strip()]
            
            valid_addresses = []
            for addr in addresses:
                if addr.startswith('0x') and len(addr) == 42:
                    valid_addresses.append(addr)
                else:
                    self.log(f"Warning: Alamat tidak valid - {addr}")
            
            return valid_addresses
        except FileNotFoundError:
            self.log("Error: File adrs.txt tidak ditemukan")
            return []
    
    def create_headers(self):
        return {
            'authority': 'campapi.diamante.io',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.6',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'access-token': 'key',
            'content-type': 'application/json',
            'cookie': self.cookie,
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
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        }
    
    def create_payload(self, to_address, amount):
        return {
            "toAddress": to_address,
            "amount": amount,
            "userId": self.user_id
        }
    
    def transfer_with_retry(self, to_address, amount, max_retries=10):
        retry_count = 0
        
        while retry_count < max_retries:
            retry_count += 1
            
            if retry_count > 1:
                retry_delay = random.randint(10, 30)
                self.log(f"Retry {retry_count}/{max_retries} untuk {to_address}")
                self.log(f"Delay {retry_delay} detik")
                time.sleep(retry_delay)
            
            try:
                payload = self.create_payload(to_address, amount)
                headers = self.create_headers()
                
                response = requests.post(
                    self.base_url,
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        return True, result
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        
                        if any(err in error_msg.lower() for err in ['rate limit', 'database', 'internal', 'timeout', 'busy']):
                            self.log(f"Error: {error_msg} (coba lagi)")
                            continue
                        else:
                            return False, result
                
                elif response.status_code == 429:
                    self.log("Rate limit exceeded (429)")
                    wait_time = random.randint(30, 60)
                    self.log(f"Menunggu {wait_time} detik")
                    time.sleep(wait_time)
                    continue
                
                elif response.status_code >= 500:
                    self.log(f"Server error {response.status_code}")
                    continue
                
                else:
                    self.log(f"HTTP {response.status_code}: {response.text}")
                    continue
                    
            except requests.exceptions.Timeout:
                self.log("Timeout, mencoba lagi")
                continue
                
            except requests.exceptions.ConnectionError:
                self.log("Connection error, mencoba lagi")
                time.sleep(15)
                continue
                
            except Exception as e:
                self.log(f"Exception: {str(e)}")
                continue
        
        return False, {"error": "Max retries reached"}
    
    def process_transfers(self, addresses, amount, min_delay, max_delay):
        total = len(addresses)
        successful = 0
        failed = []
        
        self.log(f"Memulai transfer ke {total} alamat")
        self.log(f"Amount: {amount} ETH")
        self.log(f"Delay: {min_delay}-{max_delay} detik")
        self.log("=" * 50)
        
        for i, address in enumerate(addresses, 1):
            self.log(f"Transfer {i}/{total}")
            self.log(f"Ke: {address}")
            
            success, result = self.transfer_with_retry(address, amount)
            
            if success:
                successful += 1
                self.log(f"Berhasil!")
                self.log(f"Hash: {result['data']['transferData']['hash']}")
                self.log(f"Status: {result['data']['transferData']['status']}")
                self.log(f"Nonce: {result['data']['transferData']['nonce']}")
            else:
                failed.append(address)
                self.log(f"Gagal setelah semua percobaan")
            
            if i < total:
                delay = random.randint(min_delay, max_delay)
                self.log(f"Menunggu {delay} detik")
                time.sleep(delay)
        
        self.log("=" * 50)
        self.log(f"SUMMARY")
        self.log(f"Total: {total}")
        self.log(f"Berhasil: {successful}")
        self.log(f"Gagal: {len(failed)}")
        
        if failed:
            failed_file = f"failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(failed_file, 'w') as f:
                for addr in failed:
                    f.write(addr + '\n')
            self.log(f"Alamat gagal disimpan di: {failed_file}")
    
    def get_inputs(self):
        print("\nKONFIGURASI TRANSFER")
        print("-" * 30)
        
        while True:
            amount_input = input(f"Amount ETH (default {self.default_amount}): ").strip()
            if not amount_input:
                amount = self.default_amount
                break
            try:
                amount = float(amount_input)
                if amount > 0:
                    break
                else:
                    print("Amount harus lebih dari 0")
            except:
                print("Format tidak valid")
        
        while True:
            min_delay_input = input("Min delay (detik, default 5): ").strip()
            min_delay = int(min_delay_input) if min_delay_input else 5
            
            max_delay_input = input("Max delay (detik, default 15): ").strip()
            max_delay = int(max_delay_input) if max_delay_input else 15
            
            if min_delay > 0 and max_delay > 0 and max_delay >= min_delay:
                break
            else:
                print("Delay tidak valid")
        
        while True:
            retry_input = input("Max retry (default 10): ").strip()
            max_retries = int(retry_input) if retry_input else 10
            if max_retries >= 1:
                break
            else:
                print("Minimal 1 retry")
        
        return amount, min_delay, max_delay, max_retries

def main():
    print("DIAMANTE AUTO TRANSFER BOT")
    print("=" * 40)
    
    bot = TransferBot()
    
    while True:
        print("\nMENU:")
        print("1. Mulai transfer")
        print("2. Lihat alamat")
        print("3. Keluar")
        
        choice = input("Pilih: ").strip()
        
        if choice == "1":
            addresses = bot.read_addresses()
            if not addresses:
                continue
            
            print(f"Ditemukan {len(addresses)} alamat")
            
            amount, min_delay, max_delay, max_retries = bot.get_inputs()
            
            print("\nKONFIRMASI:")
            print(f"Jumlah: {len(addresses)}")
            print(f"Amount: {amount}")
            print(f"Delay: {min_delay}-{max_delay}")
            print(f"Max retry: {max_retries}")
            
            confirm = input("Lanjut? (y/n): ").lower()
            if confirm == 'y':
                bot.process_transfers(addresses, amount, min_delay, max_delay)
            else:
                print("Dibatalkan")
        
        elif choice == "2":
            addresses = bot.read_addresses()
            if addresses:
                print(f"\nDaftar ({len(addresses)}):")
                for i, addr in enumerate(addresses[:10], 1):
                    print(f"{i:3}. {addr}")
                if len(addresses) > 10:
                    print(f"... {len(addresses)-10} lainnya")
            else:
                print("Tidak ada alamat")
        
        elif choice == "3":
            print("Keluar")
            break
        
        else:
            print("Pilihan salah")

if __name__ == "__main__":
    main()
