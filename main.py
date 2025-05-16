import customtkinter as ctk
from gui import App # Import the main application class from gui.py
import os

def main():
    # Set application appearance (can also be done directly in App.__init__)
    # "System" adapts to the OS setting
    # "Dark" or "Light" for forced dark/light mode
    ctk.set_appearance_mode("System") 
    # Color themes: "blue" (default), "green", "dark-blue"
    ctk.set_default_color_theme("blue")

    # Scaling settings for high DPI monitors (optional, if issues arise)
    # ctk.set_widget_scaling(1.0)  # Example: 1.0 for 100% scaling
    # ctk.set_window_scaling(1.0)

    # Check if assets directory exists, create it if not
    # This is to avoid errors if alert_manager or other parts expect its existence
    # during import or initialization before the GUI is fully up.
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    alert_sound_path = os.path.join(assets_dir, "allert.mp3") # Changed from allert.wav
    if not os.path.exists(assets_dir):
        try:
            os.makedirs(assets_dir)
            print(f"Directory '{assets_dir}' was created.")
            # We can also add creation of an empty alert sound file if it's missing
            if not os.path.exists(alert_sound_path):
                with open(alert_sound_path, 'w') as f:
                    pass # Just create an empty file as a placeholder
                print(f"Placeholder alert sound '{alert_sound_path}' created.")
        except OSError as e:
            print(f"Error creating directory '{assets_dir}': {e}")
    elif not os.path.exists(alert_sound_path): # If assets_dir exists, but sound file doesn't
        try:
            with open(alert_sound_path, 'w') as f:
                pass # Just create an empty file as a placeholder
            print(f"Placeholder alert sound '{alert_sound_path}' created.")
        except Exception as e:
            print(f"Could not create placeholder alert sound '{alert_sound_path}': {e}")

    app = App()
    app.mainloop()

if __name__ == "__main__":
    main() 