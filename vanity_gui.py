import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import time
from datetime import timedelta
import psutil
from solana_vanity import VanityAddressGenerator
import threading
import queue
import statistics

class VanityGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Solana Vanity - The Worst Coded Company")
        self.root.resizable(False, False)
        
        # Variables
        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.case_sensitive = tk.BooleanVar(value=True)
        self.cores_var = tk.StringVar(value=str(max(1, psutil.cpu_count() - 1)))
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.StringVar()
        
        # State variables
        self.generator = None
        self.is_running = False
        self.is_paused = False
        self.update_queue = queue.Queue()
        
        # Set up close protocol
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.create_gui()
        self.update_status()
        
    def create_gui(self):
        # Main frame with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, pady=(0, 10))
        ttk.Label(title_frame, text="Solana Vanity Generator", 
                 font=('Arial', 16, 'bold')).pack()
        ttk.Label(title_frame, text="The Worst Coded Company", 
                 font=('Arial', 10, 'italic')).pack()
        
        # System Info Frame
        sys_frame = ttk.LabelFrame(main_frame, text="System Information", padding="5")
        sys_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        
        cpu_physical = psutil.cpu_count(logical=False)
        cpu_total = psutil.cpu_count()
        memory = psutil.virtual_memory()
        
        ttk.Label(sys_frame, 
                 text=f"CPU Cores (Physical): {cpu_physical}").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Label(sys_frame, 
                 text=f"CPU Cores (with Hyperthreading): {cpu_total}").grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Label(sys_frame, 
                 text=f"Memory Available: {memory.available / (1024**3):.1f} GB").grid(row=1, column=0, sticky=tk.W, padx=5)
        ttk.Label(sys_frame, 
                 text=f"Memory Total: {memory.total / (1024**3):.1f} GB").grid(row=1, column=1, sticky=tk.W, padx=5)
        
        recommended = max(1, cpu_total - 1)
        ttk.Label(sys_frame, 
                 text=f"Recommended cores to use: {recommended}").grid(row=2, column=0, sticky=tk.W, padx=5)
        ttk.Label(sys_frame, 
                 text="Note: Using all cores may impact system performance",
                 font=('Arial', 9, 'italic')).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        # Pattern Frame
        pattern_frame = ttk.LabelFrame(main_frame, text="Search Pattern", padding="5")
        pattern_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        
        ttk.Label(pattern_frame, text="Prefix:").grid(row=0, column=0, padx=5)
        ttk.Entry(pattern_frame, textvariable=self.prefix_var, width=20).grid(row=0, column=1, padx=5)
        
        ttk.Label(pattern_frame, text="Suffix:").grid(row=0, column=2, padx=5)
        ttk.Entry(pattern_frame, textvariable=self.suffix_var, width=20).grid(row=0, column=3, padx=5)
        
        # Options Frame
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="5")
        options_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        
        ttk.Checkbutton(options_frame, text="Case Sensitive", 
                       variable=self.case_sensitive).grid(row=0, column=0, padx=5)
        
        ttk.Label(options_frame, text="CPU Cores:").grid(row=0, column=1, padx=5)
        cores_spin = ttk.Spinbox(options_frame, from_=1, to=psutil.cpu_count(),
                               textvariable=self.cores_var, width=5)
        cores_spin.grid(row=0, column=2, padx=5)
        
        # Buttons Frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=5)
        
        self.start_button = ttk.Button(button_frame, text="Start", 
                                     command=self.start_generation)
        self.start_button.pack(side=tk.LEFT, padx=2)
        
        self.pause_button = ttk.Button(button_frame, text="Pause",
                                     command=self.toggle_pause, state=tk.DISABLED)
        self.pause_button.pack(side=tk.LEFT, padx=2)
        
        self.stop_button = ttk.Button(button_frame, text="Stop",
                                    command=self.stop_generation, state=tk.DISABLED,
                                    style="Stop.TButton")
        self.stop_button.pack(side=tk.LEFT, padx=2)
        
        self.view_button = ttk.Button(button_frame, text="View Saved",
                                    command=self.view_saved)
        self.view_button.pack(side=tk.LEFT, padx=2)
        
        # Progress Frame
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.grid(row=5, column=0, columnspan=2, sticky=tk.EW, pady=(0, 5))
        
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var,
                                      wraplength=400)
        self.progress_label.pack(fill=tk.X)
        
        # Status bar
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding="2")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        
        # Style for stop button
        style = ttk.Style()
        style.configure("Stop.TButton", foreground="red")

    def update_status(self):
        try:
            while True:
                msg = self.update_queue.get_nowait()
                if 'status' in msg:
                    self.status_var.set(msg['status'])
                if 'progress' in msg:
                    self.progress_var.set(msg['progress'])
                if 'complete' in msg:
                    self.generation_complete()
        except queue.Empty:
            pass
        self.root.after(100, self.update_status)

    def start_generation(self):
        if self.is_running:
            return
            
        prefix = self.prefix_var.get().strip()
        suffix = self.suffix_var.get().strip()
        
        if not prefix and not suffix:
            messagebox.showerror("Error", "At least one pattern (prefix or suffix) must be specified")
            return
            
        try:
            cores = int(self.cores_var.get())
            if not 1 <= cores <= psutil.cpu_count():
                raise ValueError()
        except ValueError:
            messagebox.showerror("Error", f"Cores must be between 1 and {psutil.cpu_count()}")
            return
            
        # Calculate estimate
        est_seconds, combinations = VanityAddressGenerator.estimate_time(prefix, suffix, cores)
        
        msg = f"Pattern Analysis:\n\n"
        if prefix:
            msg += f"Prefix: '{prefix}'\n"
        if suffix:
            msg += f"Suffix: '{suffix}'\n"
        msg += f"Total combinations: {combinations:,}\n"
        msg += f"Estimated time: {timedelta(seconds=int(est_seconds))}\n\n"
        
        if est_seconds > 3600:
            msg += "Warning: This might take a long time!\n"
            msg += "Consider using a shorter pattern or more cores.\n\n"
            
        msg += "Do you want to proceed?"
        
        if not messagebox.askyesno("Confirm Generation", msg):
            return
            
        # Start generation
        self.is_running = True
        self.generator = VanityAddressGenerator(prefix, suffix, self.case_sensitive.get())
        
        # Update UI
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.NORMAL)
        self.view_button.config(state=tk.DISABLED)
        
        # Start generation thread
        threading.Thread(target=self.generation_thread, 
                       args=(cores,), daemon=True).start()

    def generation_thread(self, cores):
        try:
            self.update_queue.put({
                'status': 'Running',
                'progress': 'Starting generation...'
            })
            
            # Start monitoring thread for real-time updates
            stop_monitor = threading.Event()
            monitor_thread = threading.Thread(
                target=self.monitor_progress,
                args=(cores, stop_monitor),
                daemon=True
            )
            monitor_thread.start()
            
            try:
                keypair, attempts, elapsed = self.generator.generate(cores)
                stop_monitor.set()  # Stop the monitoring thread
                
                if keypair:  # If not cancelled
                    filename = f"vanity-wallet-{int(time.time())}.json"
                    VanityAddressGenerator.save_to_file(
                        keypair, filename,
                        self.prefix_var.get().strip(),
                        self.suffix_var.get().strip()
                    )
                    
                    self.update_queue.put({
                        'status': 'Complete!',
                        'progress': f"Found matching address!\n"
                                   f"Public Key: {keypair.pubkey()}\n"
                                   f"Attempts: {attempts:,}\n"
                                   f"Time: {timedelta(seconds=int(elapsed))}\n"
                                   f"Saved to: {filename}"
                    })
                
                self.update_queue.put({'complete': True})
                
            except Exception as e:
                stop_monitor.set()  # Stop the monitoring thread
                self.update_queue.put({
                    'status': 'Error occurred',
                    'progress': f"Error: {str(e)}"
                })
                self.update_queue.put({'complete': True})
                
        except Exception as e:
            self.update_queue.put({
                'status': 'Error occurred',
                'progress': f"Error: {str(e)}"
            })
            self.update_queue.put({'complete': True})

    def monitor_progress(self, cores, stop_event):
        """Monitor and update progress in real-time"""
        start_time = time.time()
        last_update = 0
        
        while not stop_event.is_set():
            if self.generator and hasattr(self.generator, 'attempts_per_sec') and self.generator.attempts_per_sec:
                current_time = time.time()
                
                # Update every 0.5 seconds
                if current_time - last_update >= 0.5:
                    # Calculate statistics
                    elapsed = current_time - start_time
                    avg_speed = sum(self.generator.attempts_per_sec) / len(self.generator.attempts_per_sec)
                    if len(self.generator.attempts_per_sec) > 1:
                        recent_speed = statistics.mean(self.generator.attempts_per_sec[-10:])
                    else:
                        recent_speed = avg_speed
                    
                    # Calculate remaining time
                    prefix = self.prefix_var.get().strip()
                    suffix = self.suffix_var.get().strip()
                    possible_combinations = 58 ** len(prefix + suffix)
                    estimated_total_attempts = possible_combinations / 2
                    total_attempts = sum(self.generator.attempts_per_sec)
                    remaining_attempts = max(0, estimated_total_attempts - total_attempts)
                    time_remaining = remaining_attempts / (recent_speed * cores)
                    
                    # Update status
                    status = "Running"
                    if self.is_paused:
                        status = "Paused"
                    
                    self.update_queue.put({
                        'status': status,
                        'progress': (
                            f"Speed: {recent_speed * cores:,.0f} addr/s\n"
                            f"Total Attempts: {total_attempts:,}\n"
                            f"Elapsed Time: {timedelta(seconds=int(elapsed))}\n"
                            f"Estimated Remaining: {timedelta(seconds=int(time_remaining))}"
                        )
                    })
                    
                    last_update = current_time
            
            time.sleep(0.1)  # Prevent high CPU usage

    def toggle_pause(self):
        if not self.generator:
            return
            
        self.is_paused = not self.is_paused
        self.generator.pause_event.set() if self.is_paused else self.generator.pause_event.clear()
        
        self.pause_button.config(text="Resume" if self.is_paused else "Pause")
        status = "Paused" if self.is_paused else "Running"
        self.update_queue.put({
            'status': status,
            'progress': f"Generation {status.lower()}"
        })

    def stop_generation(self):
        if not self.generator or not self.is_running:
            return
            
        if messagebox.askyesno("Confirm", "Stop the generation process?"):
            self.cleanup()
            self.update_queue.put({
                'status': 'Stopped',
                'progress': "Generation stopped by user",
                'complete': True
            })

    def generation_complete(self):
        self.is_running = False
        self.is_paused = False
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)
        self.view_button.config(state=tk.NORMAL)

    def view_saved(self):
        wallet_files = [f for f in os.listdir('.')
                       if f.startswith('vanity-wallet-') and f.endswith('.json')]
        
        if not wallet_files:
            messagebox.showinfo("Info", "No saved addresses found!")
            return
            
        # Create viewer window
        viewer = tk.Toplevel(self.root)
        viewer.title("Saved Addresses")
        viewer.geometry("500x400")
        viewer.transient(self.root)  # Make window modal
        viewer.grab_set()  # Make window modal
        
        # Set up close protocol for viewer window
        def on_viewer_closing():
            viewer.grab_release()
            viewer.destroy()
        
        viewer.protocol("WM_DELETE_WINDOW", on_viewer_closing)
        
        frame = ttk.Frame(viewer, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Add show private key toggle with warning
        show_frame = ttk.Frame(frame)
        show_frame.pack(fill=tk.X, pady=(0, 5))
        
        show_private = tk.BooleanVar(value=False)
        ttk.Checkbutton(show_frame, text="Show Private Keys", 
                       variable=show_private).pack(side=tk.LEFT)
        warning_label = ttk.Label(show_frame, 
                                text="Warning: Never share private keys!",
                                foreground="red")
        warning_label.pack(side=tk.LEFT, padx=10)
        warning_label.pack_forget()  # Initially hidden
        
        # Create text widget
        text = tk.Text(frame, wrap=tk.WORD, height=20)
        text.pack(fill=tk.BOTH, expand=True)
        text.config(state=tk.DISABLED)  # Make read-only
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text.config(yscrollcommand=scrollbar.set)
        
        def update_view(*args):
            text.config(state=tk.NORMAL)  # Allow editing
            text.delete(1.0, tk.END)
            
            if show_private.get():
                warning_label.pack(side=tk.LEFT, padx=10)  # Show warning
            else:
                warning_label.pack_forget()  # Hide warning
            
            for i, file in enumerate(wallet_files, 1):
                with open(file) as f:
                    data = json.load(f)
                    text.insert(tk.END, f"\n{i}. File: {file}\n")
                    text.insert(tk.END, f"   Public Key: {data['public_key']}\n")
                    if show_private.get():
                        text.insert(tk.END, f"   Private Key: {data['secret_key']}\n")
                    if "search_patterns" in data:
                        patterns = []
                        if data["search_patterns"]["prefix"]:
                            patterns.append(f"prefix='{data['search_patterns']['prefix']}'")
                        if data["search_patterns"]["suffix"]:
                            patterns.append(f"suffix='{data['search_patterns']['suffix']}'")
                        if patterns:
                            text.insert(tk.END, f"   Search Pattern: {', '.join(patterns)}\n")
            text.see(1.0)
            text.config(state=tk.DISABLED)  # Make read-only again
        
        update_view()  # Initial view
        show_private.trace_add("write", update_view)  # Modern way to trace variable changes

    def on_closing(self):
        """Handle window close event"""
        if self.is_running:
            if messagebox.askyesno("Quit", "Generation is in progress. Are you sure you want to quit?"):
                self.cleanup()
                self.root.destroy()
        else:
            self.root.destroy()

    def cleanup(self):
        """Clean up resources before closing"""
        if self.generator:
            self.generator.pause_event.set()  # Pause any running processes
            # Wait briefly for processes to clean up
            self.update_queue.put({
                'status': 'Stopping...',
                'progress': "Cleaning up processes..."
            })
            self.root.update()  # Force update to show cleanup message
            time.sleep(0.5)  # Give processes time to stop

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = VanityGUI()
    app.run() 