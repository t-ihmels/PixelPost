import pystray
from PIL import Image, ImageDraw, ImageFont # Added ImageFont
import requests
import keyboard
import tkinter as tk
from tkinter import simpledialog, ttk, messagebox  # Added messagebox here
import json
import os
import threading
import socket
import time
from zeroconf import Zeroconf, ServiceBrowser
from functools import partial

CONFIG_FILE = "pixelpost_config.json"

DEFAULT_MESSAGES = [
    "Pixel Power", "Coffee Required", "AFK - Be Right Back", 
    "Do Not Disturb", "Gaming in Progress", "Hello World", 
    "Vibe Check Passed", "Send Snacks", "Error 404 Brain", 
    "Loading", "Keep Calm and Code", "Party Mode"
]

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                conf = json.load(f)
                if "offset" not in conf: conf["offset"] = 128
                if "color_label" not in conf: conf["color_label"] = "⚪ White"
                return conf
        except: pass
    return {
        "ip": "", 
        "texts": DEFAULT_MESSAGES, 
        "hotkey": "ctrl+alt+f1", 
        "brightness": 128,
        "speed": 128,
        "offset": 128,
        "color_mode": "RGB"
    }

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)

class WLEDScanner:
    def __init__(self): self.found_devices = {}
    def add_service(self, zc, type_, name):
        info = zc.get_service_info(type_, name)
        if info: self.found_devices[name.split('.')[0]] = socket.inet_ntoa(info.addresses[0])
    def update_service(self, zc, type_, name): self.add_service(zc, type_, name)
    def remove_service(self, zc, type_, name): pass

class PixelPost:
    def __init__(self):
        self.config = load_config()
        if "text_color" not in self.config: 
            self.config["text_color"] = [255, 255, 255]
        
        self.hotkey_hook = None
        self.connected = False  
        self.icon = None
        self.setup_hotkeys()
        threading.Thread(target=self.auto_connect, daemon=True).start()
        
    def show_about(self, *args):
        """Displays the program information in a non-blocking thread."""
        def run_dialog():
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showinfo(
                "About PixelPost",
                "PixelPost v1.0\n\n"
                "© 2026 Troy Ihmels\n"
                "A text display utility for WLED Matrix displays.",
                parent=root
            )
            root.destroy()

        threading.Thread(target=run_dialog, daemon=True).start()
        
    def auto_connect(self):
        try:
            requests.get(f"http://{self.config['ip']}/json/state", timeout=2)
            self.connected = True
            if self.icon: self.icon.menu = self.create_menu()
        except: pass

    def setup_hotkeys(self):
        try:
            if self.hotkey_hook: keyboard.remove_hotkey(self.hotkey_hook)
            self.hotkey_hook = keyboard.add_hotkey(self.config["hotkey"], 
                lambda: self.prompt_custom_text() if self.connected else None)
        except: pass
        
    def set_text_color(self, r, g, b, palette, label, *args):
        print(f"\n[!!!] COLOR CLICKED: {label} (RGB: {r},{g},{b})")
        
        self.config["text_color"] = [r, g, b]
        self.config["palette"] = palette
        self.config["color_label"] = label
        save_config(self.config)

        if not self.connected:
            return

        current_text = self.config.get("last_text", "")
        url = f"http://{self.config['ip']}/json/state"
        
        data = {
            "seg": [{
                "id": 0,
                "n": current_text, 
                "col": [[r, g, b]], 
                "pal": palette,
                "sel": True
            }]
        }

        def perform_request():
            try:
                requests.post(url, json=data, timeout=2)
            except: pass

        threading.Thread(target=perform_request, daemon=True).start()

        if self.icon:
            self.icon.menu = self.create_menu()
        
    def send_to_wled(self, text=None, brightness=None, speed=None, offset=None, *args):
        # If text is an Icon (happens when pystray calls this), reset it to None
        # or handle the fact that pystray might pass icon/item as the first positional args
        if not isinstance(text, str) and text is not None:
            text = None

        if text is not None:
            self.config["last_text"] = text
            save_config(self.config)

        url = f"http://{self.config['ip']}/json/state"
        color = self.config.get("text_color", [255, 255, 255])
        palette = self.config.get("palette", 0)
        
        data = {"on": True}
        
        # Only set brightness if it's a valid number, not a pystray object
        if isinstance(brightness, (int, float)):
            data["bri"] = int(brightness)
        else:
            data["bri"] = self.config.get("brightness", 128)
        
        data["seg"] = [{
            "id": 0,
            "n": str(text) if text else self.config.get("last_text", ""),
            "col": [color, [0, 0, 0], [0, 0, 0]],
            "pal": palette,
            "fx": 122, 
            "sx": speed if isinstance(speed, (int, float)) else self.config.get("speed", 128),
            "ix": offset if isinstance(offset, (int, float)) else self.config.get("offset", 160),
            "sel": True
        }]

        def perform_request():
            try:
                resp = requests.post(url, json=data, timeout=2)
                if resp.status_code == 200:
                    if not self.connected:
                        self.connected = True
                        if self.icon: self.icon.menu = self.create_menu()
            except:
                if self.connected:
                    self.connected = False
                    if self.icon: self.icon.menu = self.create_menu()
        
        threading.Thread(target=perform_request, daemon=True).start()
        return True

    def test_connection(self, status_label, current_ip, mode):
        status_label.config(text="Capturing current state...", fg="blue")
        url = f"http://{current_ip}/json/state"
        
        previous_state = None
        try:
            resp = requests.get(url, timeout=1.5)
            if resp.status_code == 200:
                previous_state = resp.json()
                for key in ["wifi", "info", "fs", "ndc", "live"]:
                    previous_state.pop(key, None)
        except: pass

        mapping = {"RGB": [0, 255, 0], "GRB": [255, 0, 0], "BRG": [0, 0, 255]}
        color = mapping.get(mode, [0, 255, 0])
        test_payload = {"on": True, "bri": 128, "seg": [{"id": 0, "fx": 0, "col": [color]}]}
        
        try:
            requests.post(url, json=test_payload, timeout=1.5)
            status_label.config(text="Success! Matrix is Green.", fg="green")
            time.sleep(3.0)
            
            if previous_state:
                requests.post(url, json=previous_state, timeout=1.5)
                status_label.config(text="Verified", fg="green")
            else:
                self.send_to_wled(text="Test Complete")
                status_label.config(text="Verified (Default Restore)", fg="green")
                
            self.connected = True
            if self.icon: self.icon.menu = self.create_menu()
        except:
            status_label.config(text="Failed. Check IP.", fg="red")

    def prompt_custom_text(self):
        if not self.connected: return
        threading.Thread(target=self._prompt_ui, daemon=True).start()

    def _prompt_ui(self):
        root = tk.Tk()
        root.withdraw()  # Hide the main tiny window
        
        # --- THE FOCUS STACK ---
        root.attributes("-topmost", True)  # Stay on top of other windows
        root.lift()                        # Move to top of the window stack
        root.focus_force()                 # Force Windows to give us the keyboard
        
        # Now show the dialog
        user_input = simpledialog.askstring(
            "PixelPost", 
            "Enter Matrix Message:", 
            parent=root
        )
        
        if user_input: 
            self.send_to_wled(text=user_input)
            
        root.destroy()

    def _settings_ui(self):
        root = tk.Tk()
        root.title("PixelPost Settings")
        root.geometry("400x720")
        root.attributes("-topmost", True); root.lift()

        tk.Label(root, text="WLED IP Address:", font=('Segoe UI', 10, 'bold')).pack(pady=(15,0))
        ip_entry = tk.Entry(root, width=30)
        ip_entry.insert(0, self.config["ip"])
        ip_entry.pack(pady=5)

        device_cb = ttk.Combobox(root, state="readonly", width=27)
        device_cb.set("No devices found yet")
        scanner_label = tk.Label(root, text="Scan for WLED targets", fg="gray", font=('Segoe UI', 8))

        def start_scan():
            scanner_label.config(text="Searching...", fg="blue")
            scanner = WLEDScanner()
            zc = Zeroconf()
            ServiceBrowser(zc, "_wled._tcp.local.", scanner)
            threading.Event().wait(timeout=2.5)
            zc.close()
            if scanner.found_devices:
                scanner_label.config(text=f"Found {len(scanner.found_devices)} devices!", fg="green")
                device_cb['values'] = list(scanner.found_devices.keys())
                device_cb.set("Select a device...")
                device_cb.bind("<<ComboboxSelected>>", lambda e: (
                    ip_entry.delete(0, tk.END), 
                    ip_entry.insert(0, scanner.found_devices[device_cb.get()])
                ))
            else:
                scanner_label.config(text="No targets found.", fg="red")

        tk.Button(root, text="Discover Devices", command=lambda: threading.Thread(target=start_scan).start()).pack()
        scanner_label.pack()
        device_cb.pack(pady=5)

        tk.Label(root, text="Hardware Color Order:", font=('Segoe UI', 9)).pack(pady=(10,0))
        mode_cb = ttk.Combobox(root, values=["RGB", "GRB", "BRG"], state="readonly", width=10)
        mode_cb.set(self.config.get("color_mode", "RGB"))
        mode_cb.pack()

        test_status = tk.Label(root, text="Verify connection and restore state", fg="gray", font=('Segoe UI', 8))
        tk.Button(root, text="Test Connection", 
                  command=lambda: threading.Thread(target=self.test_connection, 
                  args=(test_status, ip_entry.get().strip(), mode_cb.get())).start()).pack(pady=5)
        test_status.pack()

        bri_label_text = tk.StringVar(value=f"Matrix Brightness: {self.config['brightness']}")
        speed_label_text = tk.StringVar(value=f"Scrolling Speed: {self.config['speed']}")
        off_label_text = tk.StringVar(value=f"Vertical Text Offset: {self.config['offset']}")

        def update_labels_only(*args):
            bri_label_text.set(f"Matrix Brightness: {int(bri_var.get())}")
            speed_label_text.set(f"Scrolling Speed: {int(speed_var.get())}")
            off_label_text.set(f"Vertical Text Offset: {int(off_var.get())}")

        def on_slider_release(event):
            self.config.update({
                "brightness": int(bri_var.get()),
                "speed": int(speed_var.get()),
                "offset": int(off_var.get())
            })
            self.send_to_wled(
                brightness=self.config["brightness"],
                speed=self.config["speed"],
                offset=self.config["offset"]
            )

        tk.Label(root, textvariable=bri_label_text, font=('Segoe UI', 10, 'bold')).pack(pady=(15,0))
        bri_var = tk.DoubleVar(value=self.config["brightness"])
        bri_s = ttk.Scale(root, from_=0, to=255, orient='horizontal', variable=bri_var, command=update_labels_only)
        bri_s.bind("<ButtonRelease-1>", on_slider_release)
        bri_s.pack(fill='x', padx=50)
        
        tk.Label(root, textvariable=speed_label_text, font=('Segoe UI', 10, 'bold')).pack(pady=(15,0))
        speed_var = tk.DoubleVar(value=self.config["speed"])
        speed_s = ttk.Scale(root, from_=0, to=255, orient='horizontal', variable=speed_var, command=update_labels_only)
        speed_s.bind("<ButtonRelease-1>", on_slider_release)
        speed_s.pack(fill='x', padx=50)

        tk.Label(root, textvariable=off_label_text, font=('Segoe UI', 10, 'bold')).pack(pady=(15,0))
        off_var = tk.DoubleVar(value=self.config["offset"])
        off_s = ttk.Scale(root, from_=128, to=255, orient='horizontal', variable=off_var, command=update_labels_only)
        off_s.bind("<ButtonRelease-1>", on_slider_release)
        off_s.pack(fill='x', padx=50)

        tk.Label(root, text="Saved Messages (One per line):", font=('Segoe UI', 10, 'bold')).pack(pady=(15,0))
        text_area = tk.Text(root, height=8, width=40)
        text_area.insert("1.0", "\n".join(self.config["texts"]))
        text_area.pack()

        def save_and_close():
            self.config.update({
                "ip": ip_entry.get().strip(),
                "color_mode": mode_cb.get(),
                "brightness": int(bri_var.get()),
                "speed": int(speed_var.get()),
                "offset": int(off_var.get()),
                "texts": [l.strip() for l in text_area.get("1.0", "end").split("\n") if l.strip()]
            })
            save_config(self.config)
            self.setup_hotkeys()
            if self.icon:
                self.icon.menu = self.create_menu()
            root.destroy()

        tk.Button(root, text="SAVE & APPLY", bg="#2ecc71", fg="white", 
                  font=('Segoe UI', 10, 'bold'), height=2, width=20, 
                  command=save_and_close).pack(pady=20)
        root.mainloop()

    def create_menu(self):
        rainbow_colors = [
            ("🔴 Red", (255, 0, 0)), ("🟠 Orange", (255, 127, 0)),
            ("🟡 Yellow", (255, 255, 0)), ("🟢 Green", (0, 255, 0)),
            ("🔵 Blue", (0, 0, 255)), ("🟣 Indigo", (75, 0, 130)),
            ("⚛️ Violet", (148, 0, 211)), ("⚪ White", (255, 255, 255))
        ]

        color_items = []
        for name, rgb in rainbow_colors:
            action = partial(self.set_text_color, rgb[0], rgb[1], rgb[2], 0, name)
            color_items.append(pystray.MenuItem(name, action))
        
        color_items.append(pystray.Menu.SEPARATOR)
        rb_action = partial(self.set_text_color, 0, 0, 0, 11, "🌈 Rainbow")
        color_items.append(pystray.MenuItem("🌈 Rainbow Cycle", rb_action))

        menu_items = []
        for t in self.config.get("texts", []):
            msg_action = partial(self.send_to_wled, t)
            menu_items.append(pystray.MenuItem(t, msg_action, enabled=self.connected))

        current_label = self.config.get("color_label", "⚪ White")
        menu_items.extend([
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(f"Active Color: {current_label}", pystray.Menu(*color_items), enabled=self.connected),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Custom Post...", self.prompt_custom_text, enabled=self.connected),
            pystray.MenuItem("Settings", lambda: threading.Thread(target=self._settings_ui, daemon=True).start()),
            pystray.MenuItem("About", self.show_about), # New About Item
            pystray.MenuItem("Exit", lambda i: i.stop())
        ])
        return pystray.Menu(*menu_items)
        
    def run(self):
        # 1. Create the base image
        img = Image.new('RGB', (64, 64), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # 2. Draw 7 vertical rainbow stripes
        colors = [
            (255, 0, 0),    # Red
            (255, 165, 0),  # Orange
            (255, 255, 0),  # Yellow
            (0, 255, 0),    # Green
            (0, 0, 255),    # Blue
            (75, 0, 130),   # Indigo
            (238, 130, 238) # Violet
        ]
        
        stripe_width = 64 / len(colors)
        for i, color in enumerate(colors):
            left = i * stripe_width
            right = (i + 1) * stripe_width
            draw.rectangle([left, 0, right, 64], fill=color)

        # 3. Draw the bold white "P" with a slight shadow for readability
        try:
            font = ImageFont.truetype("arialbd.ttf", 52)
            
            # Optional: Add a subtle black outline/shadow so the white 'P' 
            # stands out against the yellow/orange stripes
            shadow_offset = 2
            draw.text((32+shadow_offset, 32+shadow_offset), "P", fill=(0, 0, 0, 100), font=font, anchor="mm")
            
            # The main white P
            draw.text((32, 32), "P", fill=(255, 255, 255), font=font, anchor="mm")
        except:
            # Fallback
            draw.text((20, 10), "P", fill=(255, 255, 255))
        
        self.icon = pystray.Icon("PixelPost", img, "PixelPost", menu=self.create_menu())
        self.icon.run()

if __name__ == "__main__":
    PixelPost().run()