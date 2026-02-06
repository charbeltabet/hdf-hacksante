import keyboard
import webbrowser

BASE_URL = "http://localhost:7500/form-context"


def open_form_context(mode=None):
    """Open Edge at form-context with optional mode parameter."""
    url = BASE_URL if mode is None else f"{BASE_URL}?mode={mode}"
    print(f"Opening: {url}")
    webbrowser.open(url)  # Opens in default browser (Edge on Windows)


def on_shift_f1():
    """Shift+F1: Open form-context (no parameter)."""
    open_form_context()


def on_shift_f2():
    """Shift+F2: Open form-context with audio mode."""
    open_form_context("audio")


def on_shift_f3():
    """Shift+F3: Open form-context with image mode."""
    open_form_context("image")


def on_shift_f4():
    """Shift+F4: Open form-context with text mode."""
    open_form_context("text")


def register_shortcuts():
    """Register all keyboard shortcuts."""
    keyboard.add_hotkey("shift+f1", on_shift_f1)
    keyboard.add_hotkey("shift+f2", on_shift_f2)
    keyboard.add_hotkey("shift+f3", on_shift_f3)
    keyboard.add_hotkey("shift+f4", on_shift_f4)


def start_listener():
    """Start the keyboard listener (blocking)."""
    register_shortcuts()
    print("Shortcut listener started. Press Ctrl+C to exit.")
    print("Shortcuts:")
    print("  Shift+F1 -> form-context")
    print("  Shift+F2 -> form-context?mode=audio")
    print("  Shift+F3 -> form-context?mode=image")
    print("  Shift+F4 -> form-context?mode=text")
    keyboard.wait()


def start_listener_non_blocking():
    """Start the keyboard listener (non-blocking)."""
    register_shortcuts()
    print("Shortcut listener started (non-blocking mode).")


if __name__ == "__main__":
    start_listener()
