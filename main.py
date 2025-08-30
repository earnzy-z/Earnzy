import requests
import json
import random
import time
import secrets
import os
import sys
import threading
from queue import Queue

# --- CONFIGURATION ---
API_URL = 'https://backend.rtechnology.in/api/finish-reading/'
NUMBER_OF_THREADS = 10
REFIDS = []  # List of refids, populated below

class TermuxColors:
    RESET = '\033[0m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 15; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    ]
    return random.choice(user_agents)

def send_request(thread_id, request_count, refid, output_queue):
    post_data = {
        "refid": refid.strip(),
        "timestamp": int(time.time() * 1000),
        "nonce": secrets.token_hex(6)
    }
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'User-Agent': get_random_user_agent(),
    }
    try:
        response = requests.post(API_URL, headers=headers, json=post_data, timeout=15)
        raw_response_text = response.text if response.text else "Empty Response"
        if response.status_code in [200, 201]:
            message = f"Request #{request_count} (Thread {thread_id}, RefID: {refid[:10]}...): SUCCESS ({response.status_code})\nResponse: {raw_response_text}\n---"
            output_queue.put((message, TermuxColors.GREEN))
        else:
            message = f"Request #{request_count} (Thread {thread_id}, RefID: {refid[:10]}...): FAIL ({response.status_code})\nResponse: {raw_response_text}\n---"
            output_queue.put((message, TermuxColors.RED))
    except requests.exceptions.RequestException as e:
        message = f"Request #{request_count} (Thread {thread_id}, RefID: {refid[:10]}...): ERROR\nDetails: {e}\n---"
        output_queue.put((message, TermuxColors.RED))

def main():
    global REFIDS
    # Load refids from environment variable or file
    refids_input = os.getenv('REFIDS', '')
    if refids_input:
        REFIDS = refids_input.split(',')
    else:
        # Fallback: read from a file or prompt (for local testing)
        try:
            with open('refids.txt', 'r') as f:
                REFIDS = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("No REFIDS environment variable or refids.txt found. Please provide refids.")
            sys.exit(1)

    if not REFIDS:
        print("No refids provided. Exiting.")
        sys.exit(1)

    os.system('clear')
    print(f"{TermuxColors.CYAN}--- Concurrent Request Script ---{TermuxColors.RESET}")
    print(f"{TermuxColors.YELLOW}Using {NUMBER_OF_THREADS} threads and {len(REFIDS)} refids. Running indefinitely...{TermuxColors.RESET}\n")

    output_queue = Queue()
    request_counter = 0

    def print_output():
        while True:
            try:
                message, color = output_queue.get_nowait()
                print(f"{color}{message}{TermuxColors.RESET}")
            except:
                time.sleep(0.1)

    threading.Thread(target=print_output, daemon=True).start()

    try:
        while True:
            threads = []
            for i in range(NUMBER_OF_THREADS):
                request_counter += 1
                refid = REFIDS[request_counter % len(REFIDS)]
                thread = threading.Thread(target=send_request, args=(i + 1, request_counter, refid, output_queue))
                threads.append(thread)
                thread.start()
            for thread in threads:
                thread.join()
    except KeyboardInterrupt:
        print(f"\n\n{TermuxColors.RED}Script stopped by user. Total requests initiated: {request_counter}{TermuxColors.RESET}")
        sys.exit(0)

if __name__ == "__main__":
    main()