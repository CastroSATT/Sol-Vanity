from solders.keypair import Keypair # type: ignore
import base58
import time
import json
import os
import sys
import queue
import multiprocessing as mp
from datetime import timedelta
import statistics
import psutil
from typing import Any, Tuple
from multiprocessing.queues import Queue
from multiprocessing.synchronize import Event

class VanityAddressGenerator:
    def __init__(self, prefix: str = "", suffix: str = "", case_sensitive: bool = True):
        self.prefix = prefix
        self.suffix = suffix
        self.case_sensitive = case_sensitive
        self.attempts_per_sec = []
        self.pause_event = mp.Event()  # New pause event

    def check_match(self, public_key: str) -> bool:
        if not self.case_sensitive:
            public_key = public_key.lower()
            prefix = self.prefix.lower()
            suffix = self.suffix.lower()
        else:
            prefix = self.prefix
            suffix = self.suffix

        matches_prefix = True if not prefix else public_key.startswith(prefix)
        matches_suffix = True if not suffix else public_key.endswith(suffix)
        
        return matches_prefix and matches_suffix

    def worker_process(self, result_queue: Queue, stop_event: Event) -> None:
        attempts = 0
        start_time = time.time()
        
        while not stop_event.is_set():
            if self.pause_event.is_set():
                time.sleep(0.1)
                continue

            attempts += 1
            keypair = Keypair()
            public_key = str(keypair.pubkey())
            
            if self.check_match(public_key):
                result_queue.put(('SUCCESS', keypair, attempts))
                return
            
            # Calculate speed every second
            if time.time() - start_time >= 1:
                speed = attempts / (time.time() - start_time)
                result_queue.put(('SPEED', speed, attempts))
                attempts = 0
                start_time = time.time()

    def generate(self, num_cores: int) -> Tuple[Keypair, int, float]:
        mp.freeze_support()  # For Windows support
        result_queue = mp.Queue()
        stop_event = mp.Event()
        self.pause_event.clear()  # Initialize as unpaused
        
        # Calculate and show initial estimate
        est_seconds, combinations = self.estimate_time(self.prefix, self.suffix, num_cores)
        if est_seconds == float('inf'):
            print("\nError: Invalid pattern! Only Base58 characters are allowed.")
            print("Valid characters: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")
            return None, 0, 0
            
        print(f"\nPattern Analysis:")
        print(f"Total possible combinations: {combinations:,}")
        print(f"Estimated time (average case): {timedelta(seconds=int(est_seconds))}")
        if est_seconds > 3600 * 24:  # More than a day
            print("\nWarning: This pattern might take a very long time!")
            print("Consider using a shorter pattern or more CPU cores.")
        
        print("\nPress 'p' to pause/resume")
        print("Press 'q' to quit to main menu")
        print("Generation starting...\n")
        
        # Start worker processes
        processes = []
        for _ in range(num_cores):
            p = mp.Process(target=self.worker_process, args=(result_queue, stop_event))
            p.start()
            processes.append(p)

        total_attempts = 0
        start_time = time.time()
        found_keypair = None
        paused_time = 0
        last_pause = 0
        
        try:
            while True:
                # Check for keyboard input
                if os.name == 'nt':  # Windows
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode().lower()
                        if key == 'p':
                            self.pause_event.set() if not self.pause_event.is_set() else self.pause_event.clear()
                        elif key == 'q':
                            if self.pause_event.is_set():
                                print("\rDo you want to quit to main menu? (y/n): ", end="")
                            else:
                                self.pause_event.set()  # Pause first
                                print("\rPaused. Do you want to quit to main menu? (y/n): ", end="")
                            
                            while True:
                                if msvcrt.kbhit():
                                    confirm = msvcrt.getch().decode().lower()
                                    if confirm == 'y':
                                        print("\nReturning to main menu...")
                                        stop_event.set()
                                        for p in processes:
                                            p.terminate()
                                        return None, total_attempts, time.time() - start_time - paused_time
                                    elif confirm == 'n':
                                        if not self.pause_event.is_set():
                                            self.pause_event.clear()  # Resume if we were not paused before
                                        break
                else:  # Unix-like
                    import select
                    if select.select([sys.stdin], [], [], 0.0)[0]:
                        key = sys.stdin.read(1).lower()
                        if key == 'p':
                            self.pause_event.set() if not self.pause_event.is_set() else self.pause_event.clear()
                        elif key == 'q':
                            if self.pause_event.is_set():
                                print("\rDo you want to quit to main menu? (y/n): ", end="")
                            else:
                                self.pause_event.set()  # Pause first
                                print("\rPaused. Do you want to quit to main menu? (y/n): ", end="")
                            
                            while True:
                                if select.select([sys.stdin], [], [], 0.0)[0]:
                                    confirm = sys.stdin.read(1).lower()
                                    if confirm == 'y':
                                        print("\nReturning to main menu...")
                                        stop_event.set()
                                        for p in processes:
                                            p.terminate()
                                        return None, total_attempts, time.time() - start_time - paused_time
                                    elif confirm == 'n':
                                        if not self.pause_event.is_set():
                                            self.pause_event.clear()  # Resume if we were not paused before
                                        break

                if self.pause_event.is_set():
                    if last_pause == 0:
                        last_pause = time.time()
                        print("\r\033[33m[PAUSED]\033[0m Press 'p' to resume or 'q' to quit", end=" "*50)
                    time.sleep(0.1)
                    continue
                elif last_pause > 0:
                    paused_time += time.time() - last_pause
                    last_pause = 0
                    print("\r\033[32m[RESUMED]\033[0m", end=" "*50)

                try:
                    result = result_queue.get_nowait()
                    if result[0] == 'SUCCESS':
                        stop_event.set()
                        found_keypair = result[1]
                        total_attempts += result[2]
                        break
                    else:  # SPEED update
                        self.attempts_per_sec.append(result[1])
                        total_attempts += result[2]
                except queue.Empty:
                    continue
                
                # Calculate and display statistics
                elapsed = time.time() - start_time - paused_time
                avg_speed = sum(self.attempts_per_sec) / len(self.attempts_per_sec)
                if len(self.attempts_per_sec) > 1:
                    recent_speed = statistics.mean(self.attempts_per_sec[-10:])
                else:
                    recent_speed = avg_speed
                
                # Estimate time remaining based on probability
                possible_combinations = 58 ** len(self.prefix + self.suffix)  # Base58 encoding
                estimated_total_attempts = possible_combinations / 2  # Average case
                remaining_attempts = max(0, estimated_total_attempts - total_attempts)
                time_remaining = remaining_attempts / (recent_speed * num_cores)
                
                # Clear line and update progress
                status = "\033[32m[RUNNING]\033[0m"  # Green color for running
                print(f"\r{status} Speed: {recent_speed * num_cores:,.0f} addr/s | "
                      f"Total: {total_attempts:,} | "
                      f"Elapsed: {timedelta(seconds=int(elapsed))} | "
                      f"Est. Remaining: {timedelta(seconds=int(time_remaining))} | "
                      f"Press 'p' to pause/resume or 'q' to quit", 
                      end="")

        finally:
            stop_event.set()
            for p in processes:
                p.terminate()
                p.join()

        return found_keypair, total_attempts, time.time() - start_time - paused_time

    @staticmethod
    def save_to_file(keypair: Keypair, filename: str, prefix: str = "", suffix: str = ""):
        secret_key = base58.b58encode(bytes(keypair.secret())).decode('ascii')
        wallet_data = {
            "public_key": str(keypair.pubkey()),
            "secret_key": secret_key,
            "search_patterns": {
                "prefix": prefix,
                "suffix": suffix
            }
        }
        with open(filename, 'w') as f:
            json.dump(wallet_data, f, indent=2)

    @staticmethod
    def estimate_time(prefix: str, suffix: str, num_cores: int) -> Tuple[float, int]:
        """Calculate a more accurate time estimate based on pattern complexity"""
        # Base58 character set (numbers + lowercase + uppercase, excluding 0OIl)
        BASE58_CHARS = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        
        # Calculate prefix probability
        prefix_prob = 1.0
        if prefix:
            for char in prefix:
                if char in BASE58_CHARS:
                    prefix_prob *= (1.0 / 58)  # Exact match needed
                else:
                    return float('inf'), 0  # Invalid character
        
        # Calculate suffix probability
        suffix_prob = 1.0
        if suffix:
            for char in suffix:
                if char in BASE58_CHARS:
                    suffix_prob *= (1.0 / 58)  # Exact match needed
                else:
                    return float('inf'), 0  # Invalid character
        
        # Total probability is the product of both probabilities
        total_prob = prefix_prob * suffix_prob
        
        # Calculate total possible combinations
        pattern_length = len(prefix + suffix)
        possible_combinations = 58 ** pattern_length if pattern_length > 0 else 0
        
        # Expected number of attempts needed (using geometric distribution mean)
        expected_attempts = 1.0 / total_prob if total_prob > 0 else float('inf')
        
        # Calculate speed based on hardware capabilities
        # Base speed of 150,000 attempts per core per second on average hardware
        # Adjust based on pattern length (longer patterns = slightly slower per attempt)
        base_speed = 150000  # Base attempts per core per second
        length_penalty = max(0.95, 1.0 - (pattern_length * 0.01))  # 1% slowdown per character
        adjusted_speed = base_speed * length_penalty * num_cores
        
        # Calculate estimated time
        estimated_seconds = expected_attempts / adjusted_speed
        
        return estimated_seconds, possible_combinations

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    banner = """
    ╔═══════════════════════════════════════╗
    ║        Solana Vanity Generator        ║
    ║    "The Worst Coded Company" Prod.    ║
    ╚═══════════════════════════════════════╝
    """
    print(banner)

def get_menu_choice():
    print("\nOptions:")
    print("1. Generate new vanity address")
    print("2. View saved addresses")
    print("3. Exit")
    while True:
        try:
            choice = int(input("\nEnter your choice (1-3): "))
            if 1 <= choice <= 3:
                return choice
            print("Please enter a number between 1 and 3")
        except ValueError:
            print("Please enter a valid number")

def reset_terminal():
    # Reset terminal settings for Unix-like systems
    if os.name != 'nt':
        import termios
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, termios.tcgetattr(sys.stdin))
        # Force terminal to echo input
        os.system('stty echo')

def main():
    try:
        while True:
            clear_screen()
            print_banner()
            print_system_info()  # Add system info display
            
            choice = get_menu_choice()
            
            if choice == 1:
                generate_new_address()
                reset_terminal()  # Reset terminal after generation
            elif choice == 2:
                view_saved_addresses()
            else:
                print("\nGoodbye!")
                break
    finally:
        reset_terminal()  # Ensure terminal is reset even if program crashes

def generate_new_address():
    clear_screen()
    print_banner()
    print("\nGenerate New Vanity Address")
    print("---------------------------")
    
    print("\nSearch Options:")
    print("1. Prefix only")
    print("2. Suffix only")
    print("3. Both prefix and suffix")
    
    while True:
        try:
            search_type = int(input("\nChoose search type (1-3): "))
            if 1 <= search_type <= 3:
                break
            print("Please enter a number between 1 and 3")
        except ValueError:
            print("Please enter a valid number")

    prefix = ""
    suffix = ""
    
    if search_type in [1, 3]:
        prefix = input("\nEnter prefix pattern: ").strip()
    if search_type in [2, 3]:
        suffix = input("Enter suffix pattern: ").strip()

    if not prefix and not suffix:
        print("At least one pattern must be specified!")
        input("\nPress Enter to continue...")
        return

    case_sensitive = input("\nCase sensitive? (y/n): ").lower() == 'y'
    
    # Get number of cores to use
    max_cores = mp.cpu_count()
    while True:
        try:
            num_cores = int(input(f"\nNumber of CPU cores to use (1-{max_cores}): "))
            if 1 <= num_cores <= max_cores:
                break
            print(f"Please enter a number between 1 and {max_cores}")
        except ValueError:
            print("Please enter a valid number")

    # Calculate and show time estimate
    est_seconds, combinations = VanityAddressGenerator.estimate_time(prefix, suffix, num_cores)
    print("\nPattern Analysis:")
    print("-----------------")
    print(f"Total possible combinations: {combinations:,}")
    print(f"Estimated time to find (average case): {timedelta(seconds=int(est_seconds))}")
    
    if est_seconds > 3600:  # If estimated time is more than an hour
        print("\nWarning: This pattern might take a long time to generate!")
        print("Consider using a shorter pattern or more CPU cores.")
    
    proceed = input("\nDo you want to proceed with generation? (y/n): ").lower()
    if proceed != 'y':
        print("\nGeneration cancelled.")
        input("\nPress Enter to continue...")
        return

    search_desc = []
    if prefix:
        search_desc.append(f"starting with '{prefix}'")
    if suffix:
        search_desc.append(f"ending with '{suffix}'")
    
    print(f"\nGenerating vanity address {' and '.join(search_desc)}")
    print("This might take a while depending on the pattern length...")
    print(f"Using {num_cores} CPU cores")
    print("Press 'p' to pause/resume generation\n")
    
    # Disable terminal echo for Unix-like systems before generation
    if os.name != 'nt':
        os.system('stty -echo')
    
    try:
        generator = VanityAddressGenerator(prefix, suffix, case_sensitive)
        keypair, attempts, elapsed = generator.generate(num_cores)
        
        if keypair:  # Only if generation wasn't cancelled
            print("\n\nFound matching address!")
            print(f"Public Key: {keypair.pubkey()}")
            print(f"Total Attempts: {attempts:,}")
            print(f"Time taken: {timedelta(seconds=int(elapsed))}")

            # Save the keypair with search patterns
            filename = f"vanity-wallet-{int(time.time())}.json"
            VanityAddressGenerator.save_to_file(keypair, filename, prefix, suffix)
            print(f"\nKeypair saved to {filename}")
    finally:
        # Re-enable terminal echo for Unix-like systems
        if os.name != 'nt':
            os.system('stty echo')
    
    input("\nPress Enter to continue...")

def view_saved_addresses():
    clear_screen()
    print_banner()
    print("\nSaved Addresses")
    print("--------------")
    
    wallet_files = [f for f in os.listdir('.') if f.startswith('vanity-wallet-') and f.endswith('.json')]
    
    if not wallet_files:
        print("\nNo saved addresses found!")
        input("\nPress Enter to continue...")
        return
    
    show_private = input("\nShow private keys? (y/n): ").lower() == 'y'
    if show_private:
        print("\nWarning: Never share your private keys with anyone!")
        print("They provide full access to your wallet.\n")
        
    for i, file in enumerate(wallet_files, 1):
        with open(file, 'r') as f:
            data = json.load(f)
            print(f"\n{i}. File: {file}")
            print(f"   Public Key: {data['public_key']}")
            if show_private:
                print(f"   Private Key: {data['secret_key']}")
            
            # Display search patterns if they exist in the file
            if "search_patterns" in data:
                patterns = []
                if data["search_patterns"]["prefix"]:
                    patterns.append(f"prefix='{data['search_patterns']['prefix']}'")
                if data["search_patterns"]["suffix"]:
                    patterns.append(f"suffix='{data['search_patterns']['suffix']}'")
                if patterns:
                    print(f"   Search Pattern: {', '.join(patterns)}")
    
    input("\nPress Enter to continue...")

def print_system_info():
    cpu_count = mp.cpu_count()
    cpu_physical = psutil.cpu_count(logical=False)
    memory = psutil.virtual_memory()
    
    print("\nSystem Information:")
    print("------------------")
    print(f"CPU Cores (Physical): {cpu_physical}")
    print(f"CPU Cores (Total with Hyperthreading): {cpu_count}")
    print(f"CPU Current Usage: {psutil.cpu_percent()}%")
    print(f"Memory Available: {memory.available / (1024**3):.1f} GB")
    print(f"Memory Total: {memory.total / (1024**3):.1f} GB")
    print(f"\nRecommended cores to use: {max(1, cpu_count - 1)}")
    print("Note: Using all cores may impact system performance")

if __name__ == "__main__":
    main() 