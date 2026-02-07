# PixelPost 🌈

**PixelPost** is a lightweight Windows system tray utility designed to control WLED-powered LED matrices. It allows you to push scrolling text messages, change colors, and manage hardware settings without ever opening a web browser.

## 🚀 Features

* **Global Hotkey:** Press `Ctrl+Alt+F1` (customizable) to pop up a message prompt instantly.
* **Dynamic Tray Icon:** A vibrant rainbow icon with a bold 'P' indicator for easy identification.
* **Live Settings:** Adjust brightness, scroll speed, and vertical offset via sliders with real-time feedback.
* **WLED Discovery:** Automatically finds WLED devices on your local network using Zeroconf/mDNS.
* **Color & Palette Control:** Switch between solid colors or Rainbow cycles directly from the menu.
* **Auto-Sync:** Saves your favorite messages and last-used settings to a local JSON configuration file.

## 🛠 Prerequisites

* **Hardware:** A WLED-enabled LED matrix (e.g., WS2812B).
* **Software:** Python 3.10 or higher.

## 📥 Installation

1. Clone or download this repository.
2. Install the required Python libraries using pip:

 ` ``bash
pip install pystray Pillow requests keyboard zeroconf
 ` ``

## 📖 Usage

1. **Initial Setup:** Launch the script. If no IP is configured, the tray icon will appear but features will be disabled until connected.
2. **Discovery:** Right-click the tray icon, go to **Settings**, and click **Discover Devices** to find your WLED IP.
3. **Hardware Test:** Select your color order (RGB/GRB/BRG) and use **Test Connection**. The matrix should turn green if configured correctly.
4. **Sending Text:**
    * Right-click the icon and select a **Saved Message**.
    * Use the **Hotkey** (`Ctrl+Alt+F1`) to type a custom message.
    * Use **Custom Post...** from the menu.
5. **Managing Colors:**
    * Hover over **Active Color** in the tray menu to select from a list of presets (Red, Green, Blue, etc.).
    * Select **Rainbow Cycle** to apply a dynamic multi-color effect to your scrolling text.

## 📦 Building the Executable

To create a standalone `.exe` for Windows, use PyInstaller:

 ```bash
python -m PyInstaller --noconfirm --onefile --windowed --name "PixelPost" --icon="icon.ico" --collect-all zeroconf pixelpost.py
 ```

> [!IMPORTANT]
> Because the `keyboard` library hooks into system-level inputs, the compiled EXE may require **Run as Administrator** to capture hotkeys while certain high-privilege windows (like Task Manager) are in focus.

## ⚙️ Configuration

Settings are stored in `pixelpost_config.json`. You can manually edit this file to change the hotkey or manage your list of saved messages.

## 📜 License

This project is licensed under the **GPL-3.0 License**. See the `LICENSE` file for details.

## 🤝 Acknowledgments

* Inspired by the [WLED Project](https://github.com/Aircoookie/WLED).
* Built with Python, Pillow, and pystray.
