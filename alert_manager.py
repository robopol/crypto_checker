import pygame
import os
import threading

# Path to the sound file
# We assume alert_manager.py is in the same directory as assets/ and the main scripts
sound_file = os.path.join(os.path.dirname(__file__), "assets", "allert.mp3")

class AlertManager:
    def __init__(self, gui_callback_visual_alert=None, sound_enabled_check_callback=None):
        """
        Args:
            gui_callback_visual_alert (function, optional): GUI function to display a visual alert.
                                                            Should accept (symbol, message, alert_type ['above'/'below'/'error'])
            sound_enabled_check_callback (function, optional): Function that returns True if sounds are enabled, otherwise False.
        """
        self.triggered_alerts = {} # Stores whether an alert for a given coin and type (above/below) has already been triggered
                                   # e.g., {"BTC_above_40000": True}
        self.gui_callback_visual_alert = gui_callback_visual_alert
        self.sound_enabled_check_callback = sound_enabled_check_callback
        
        # Initialize pygame mixer
        try:
            pygame.mixer.init()
            print("Pygame mixer initialized.")
        except pygame.error as e:
            print(f"Error initializing pygame mixer: {e}")
            # Optionally, notify GUI about this critical error
            if self.gui_callback_visual_alert:
                self.gui_callback_visual_alert("Sound System Error", f"Pygame mixer init failed: {e}", "error")
            # Sound will not work if mixer fails to init
            self._mixer_initialized = False 
        else:
            self._mixer_initialized = True

    def play_alert_sound(self):
        if not self._mixer_initialized:
            print("Pygame mixer not initialized. Cannot play sound.")
            return
            
        if not self.sound_enabled_check_callback or not self.sound_enabled_check_callback():
            # print("Sound alerts are disabled in config.")
            return

        if not os.path.exists(sound_file):
            print(f"Alert sound file not found: {sound_file}")
            if self.gui_callback_visual_alert:
                self.gui_callback_visual_alert("Sound Error", f"File not found: {os.path.basename(sound_file)}", "error")
            return

        try:
            # Using a thread to prevent GUI freeze, though pygame.mixer.Sound.play() is generally non-blocking
            # However, loading the sound might take a moment, so keeping the thread is safer.
            sound_thread = threading.Thread(target=self._actually_play_sound, args=(sound_file,))
            sound_thread.daemon = True
            sound_thread.start()
        except Exception as e: # Broad exception for unforeseen issues during thread start
            print(f"Error initiating sound playback thread: {e}")
            if self.gui_callback_visual_alert:
                 self.gui_callback_visual_alert("Sound Error", f"Playback thread error: {e}", "error")

    def _actually_play_sound(self, sound_file_path):
        if not self._mixer_initialized:
            return # Guard against playing if mixer failed

        try:
            # pygame.mixer.Sound can raise an error if the file is not found or format is bad
            alert_sound = pygame.mixer.Sound(sound_file_path)
            alert_sound.play()
        except pygame.error as e: # Specific pygame errors
            print(f"Error playing sound '{sound_file_path}' with pygame: {e}")
            if self.gui_callback_visual_alert: # Notify GUI if possible
                 self.gui_callback_visual_alert("Sound Error", f"Pygame playback error: {e}", "error")
        except Exception as e: # Other potential errors
            print(f"Unexpected error playing sound '{sound_file_path}': {e}")
            if self.gui_callback_visual_alert:
                 self.gui_callback_visual_alert("Sound Error", f"Unexpected playback error: {e}", "error")

    def check_and_trigger_alerts(self, coin_symbol, coin_id, current_price, coin_config):
        """Checks and triggers alerts for the given cryptocurrency.

        Args:
            coin_symbol (str): Cryptocurrency symbol (e.g., "BTC").
            coin_id (int): Cryptocurrency ID from CoinMarketCap.
            current_price (float): Current price of the cryptocurrency.
            coin_config (dict): Configuration for the given cryptocurrency, e.g.:
                { "symbol": "BTC", "id": 1, "alert_above": 50000, "alert_below": 30000, "alert_active": True }
        """
        if not coin_config.get("alert_active") or current_price is None:
            return

        alert_key_base = f"{coin_symbol}_{coin_id}" # Unique key for the coin

        # Check upper limit
        alert_above_price = coin_config.get("alert_above")
        if alert_above_price is not None and current_price > alert_above_price:
            alert_id = f"{alert_key_base}_above_{alert_above_price}"
            if not self.triggered_alerts.get(alert_id):
                message = f"{coin_symbol} has exceeded the price of ${alert_above_price:,.2f}! Current price: ${current_price:,.2f}"
                print(f"ALERT: {message}")
                if self.sound_enabled_check_callback and self.sound_enabled_check_callback():
                    self.play_alert_sound()
                if self.gui_callback_visual_alert:
                    self.gui_callback_visual_alert(coin_symbol, message, "above")
                self.triggered_alerts[alert_id] = True # Mark that the alert was triggered
        else:
            # Reset triggered_alerts if the price falls below the upper limit (so it can be triggered again)
            if alert_above_price is not None:
                 self.triggered_alerts.pop(f"{alert_key_base}_above_{alert_above_price}", None)

        # Check lower limit
        alert_below_price = coin_config.get("alert_below")
        if alert_below_price is not None and current_price < alert_below_price:
            alert_id = f"{alert_key_base}_below_{alert_below_price}"
            if not self.triggered_alerts.get(alert_id):
                message = f"{coin_symbol} has fallen below the price of ${alert_below_price:,.2f}! Current price: ${current_price:.2f}"
                print(f"ALERT: {message}")
                if self.sound_enabled_check_callback and self.sound_enabled_check_callback():
                    self.play_alert_sound()
                if self.gui_callback_visual_alert:
                    self.gui_callback_visual_alert(coin_symbol, message, "below")
                self.triggered_alerts[alert_id] = True # Mark that the alert was triggered
        else:
            # Reset triggered_alerts if the price rises above the lower limit
            if alert_below_price is not None:
                self.triggered_alerts.pop(f"{alert_key_base}_below_{alert_below_price}", None)

    def reset_alert_state(self, coin_symbol, coin_id, limit_type, limit_value):
        """Resets the trigger state for a specific alert if its value changes or it is deactivated.
        This is important so that after changing a limit, the alert can be triggered again.
        """
        alert_key_base = f"{coin_symbol}_{coin_id}"
        alert_id = f"{alert_key_base}_{limit_type}_{limit_value}"
        if alert_id in self.triggered_alerts:
            del self.triggered_alerts[alert_id]
            print(f"Alert state reset for {alert_id}")

    def reset_all_alerts_for_coin(self, coin_symbol, coin_id):
        """Resets all triggered alerts for a given coin (e.g., when removing the coin)."""
        prefix_to_remove = f"{coin_symbol}_{coin_id}_"
        keys_to_remove = [key for key in self.triggered_alerts if key.startswith(prefix_to_remove)]
        for key in keys_to_remove:
            del self.triggered_alerts[key]
        if keys_to_remove:
            print(f"All alerts for {coin_symbol} have been reset.")

# --- Testing (example) ---
def mock_visual_alert(symbol, message, alert_type):
    print(f"GUI Visual Alert: [{alert_type.upper()}] {symbol} - {message}")

def mock_sound_enabled(): return True

if __name__ == '__main__':
    alert_manager = AlertManager(gui_callback_visual_alert=mock_visual_alert, sound_enabled_check_callback=mock_sound_enabled)

    btc_config_1 = {"symbol": "BTC", "id": 1, "alert_above": 40000, "alert_below": 35000, "alert_active": True}
    eth_config_1 = {"symbol": "ETH", "id": 1027, "alert_above": 3000, "alert_below": None, "alert_active": True}
    ada_config_1 = {"symbol": "ADA", "id": 2010, "alert_above": None, "alert_below": 0.8, "alert_active": False} # Inactive alert
    
    print("--- Scenario 1: BTC above limit ---")
    alert_manager.check_and_trigger_alerts("BTC", 1, 41000, btc_config_1)
    alert_manager.check_and_trigger_alerts("BTC", 1, 41500, btc_config_1) # Should not trigger again immediately
    print(f"Triggered alerts: {alert_manager.triggered_alerts}")

    print("\n--- Scenario 2: BTC falls below upper limit and then rises above again (should trigger) ---")
    alert_manager.check_and_trigger_alerts("BTC", 1, 39000, btc_config_1) # Resets upper alert
    print(f"Triggered alerts after drop: {alert_manager.triggered_alerts}")
    alert_manager.check_and_trigger_alerts("BTC", 1, 41000, btc_config_1) # Should trigger again
    print(f"Triggered alerts after subsequent rise: {alert_manager.triggered_alerts}")

    print("\n--- Scenario 3: ETH above limit ---")
    alert_manager.check_and_trigger_alerts("ETH", 1027, 3100, eth_config_1)
    print(f"Triggered alerts: {alert_manager.triggered_alerts}")

    print("\n--- Scenario 4: ADA below limit (but alert is inactive) ---")
    alert_manager.check_and_trigger_alerts("ADA", 2010, 0.7, ada_config_1)
    print(f"Triggered alerts (ADA should not be present): {alert_manager.triggered_alerts}")

    print("\n--- Scenario 5: BTC below lower limit ---")
    btc_config_2 = {"symbol": "BTC", "id": 1, "alert_above": 40000, "alert_below": 35000, "alert_active": True}
    alert_manager.reset_all_alerts_for_coin("BTC", 1) # Reset for a clean test
    alert_manager.check_and_trigger_alerts("BTC", 1, 34000, btc_config_2)
    print(f"Triggered alerts: {alert_manager.triggered_alerts}")

    print("\n--- Scenario 6: Reset specific alert ---")
    alert_manager.reset_alert_state("BTC", 1, "below", 35000)
    print(f"Triggered alerts after reset: {alert_manager.triggered_alerts}")
    alert_manager.check_and_trigger_alerts("BTC", 1, 33000, btc_config_2) # Should trigger again
    print(f"Triggered alerts: {alert_manager.triggered_alerts}")

    # Test if sound file exists (informational only)
    if not os.path.exists(sound_file):
        print(f"WARNING: Sound file {sound_file} does not exist. Sound alerts will not function correctly.")
    else:
        print(f"Sound file {sound_file} found.")        