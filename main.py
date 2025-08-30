import requests
import json
import random
import time
import secrets
import os
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox
from queue import Queue

# --- CONFIGURATION ---
API_URL = 'https://backend.rtechnology.in/api/finish-reading/'
NUMBER_OF_THREADS = 10  # Number of concurrent workers.

class TermuxColors:
    RESET = '\033[0m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'

# For GUI, we'll simulate colored output in the text area
class GuiColors:
    GREEN = 'green'
    RED = 'red'
    YELLOW = 'yellow'
    CYAN = 'cyan'

def get_random_user_agent():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Linux; Android 15; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
    ]
    return random.choice(user_agents)

def send_request(thread_id, request_count, refid, output_queue):
    """The function that each thread will execute."""
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
            output_queue.put((message, GuiColors.GREEN))
        else:
            message = f"Request #{request_count} (Thread {thread_id}, RefID: {refid[:10]}...): FAIL ({response.status_code})\nResponse: {raw_response_text}\n---"
            output_queue.put((message, GuiColors.RED))
            
    except requests.exceptions.RequestException as e:
        message = f"Request #{request_count} (Thread {thread_id}, RefID: {refid[:10]}...): ERROR\nDetails: {e}\n---"
        output_queue.put((message, GuiColors.RED))

class RequestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Concurrent Request Sender")
        self.root.geometry("800x600")
        self.refids = []
        self.is_running = False
        self.output_queue = Queue()

        # GUI Components
        self.setup_gui()
        
        # Start the output queue processor
        self.process_output_queue()

    def setup_gui(self):
        # RefID Input
        tk.Label(self.root, text="Enter RefID:").pack(pady=5)
        self.refid_entry = tk.Entry(self.root, width=80)
        self.refid_entry.pack(pady=5)

        # Add RefID Button
        tk.Button(self.root, text="Add RefID", command=self.add_refid).pack(pady=5)

        # RefID Listbox
        tk.Label(self.root, text="RefIDs to Process:").pack(pady=5)
        self.refid_listbox = tk.Listbox(self.root, width=80, height=5)
        self.refid_listbox.pack(pady=5)

        # Remove Selected RefID Button
        tk.Button(self.root, text="Remove Selected RefID", command=self.remove_refid).pack(pady=5)

        # Submit Button
        self.submit_button = tk.Button(self.root, text="Start Sending Requests", command=self.start_requests)
        self.submit_button.pack(pady=10)

        # Output Area
        tk.Label(self.root, text="Output:").pack(pady=5)
        self.output_text = scrolledtext.ScrolledText(self.root, width=80, height=20, state='disabled')
        self.output_text.pack(pady=5)
        self.output_text.tag_configure(GuiColors.GREEN, foreground=GuiColors.GREEN)
        self.output_text.tag_configure(GuiColors.RED, foreground=GuiColors.RED)
        self.output_text.tag_configure(GuiColors.YELLOW, foreground=GuiColors.YELLOW)
        self.output_text.tag_configure(GuiColors.CYAN, foreground=GuiColors.CYAN)

    def add_refid(self):
        refid = self.refid_entry.get().strip()
        if refid:
            self.refids.append(refid)
            self.refid_listbox.insert(tk.END, refid[:30] + "..." if len(refid) > 30 else refid)
            self.refid_entry.delete(0, tk.END)
            self.log_message(f"Added RefID: {refid[:10]}...\n", GuiColors.CYAN)
        else:
            messagebox.showwarning("Input Error", "Please enter a valid RefID.")

    def remove_refid(self):
        try:
            selected_index = self.refid_listbox.curselection()[0]
            refid = self.refids.pop(selected_index)
            self.refid_listbox.delete(selected_index)
            self.log_message(f"Removed RefID: {refid[:10]}...\n", GuiColors.YELLOW)
        except IndexError:
            messagebox.showwarning("Selection Error", "Please select a RefID to remove.")

    def log_message(self, message, color):
        self.output_text.configure(state='normal')
        self.output_text.insert(tk.END, message, color)
        self.output_text.configure(state='disabled')
        self.output_text.see(tk.END)

    def process_output_queue(self):
        try:
            while not self.output_queue.empty():
                message, color = self.output_queue.get_nowait()
                self.log_message(message, color)
        except:
            pass
        self.root.after(100, self.process_output_queue)

    def start_requests(self):
        if not self.refids:
            messagebox.showerror("Error", "No RefIDs added. Please add at least one RefID.")
            return

        if self.is_running:
            messagebox.showinfo("Info", "Requests are already running.")
            return

        self.is_running = True
        self.submit_button.config(state='disabled')
        self.log_message(f"--- Starting Concurrent Request Script with {NUMBER_OF_THREADS} threads ---\n", GuiColors.CYAN)
        self.log_message(f"Total RefIDs: {len(self.refids)}. Press Ctrl+C in the console to stop.\n\n", GuiColors.YELLOW)

        def run_requests():
            request_counter = 0
            try:
                while self.is_running:
                    threads = []
                    # Iterate over refids cyclically
                    for i in range(NUMBER_OF_THREADS):
                        if not self.is_running:
                            break
                        request_counter += 1
                        # Cycle through refids
                        refid = self.refids[request_counter % len(self.refids)]
                        thread = threading.Thread(target=send_request, args=(i + 1, request_counter, refid, self.output_queue))
                        threads.append(thread)
                        thread.start()

                    for thread in threads:
                        thread.join()

            except KeyboardInterrupt:
                self.log_message(f"\nScript stopped by user. Total requests initiated: {request_counter}\n", GuiColors.RED)
            finally:
                self.is_running = False
                self.submit_button.config(state='normal')
                self.root.after(0, lambda: self.log_message("Request process stopped.\n", GuiColors.RED))

        # Run the requests in a separate thread to keep GUI responsive
        threading.Thread(target=run_requests, daemon=True).start()

def main():
    root = tk.Tk()
    app = RequestApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()