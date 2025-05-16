import json
import os

CONFIG_FILE_NAME = "config.json"
# Determine the absolute path to the directory containing this script
# This ensures that the config file is always looked for/created next to this script
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, CONFIG_FILE_NAME)

DEFAULT_CONFIG = {
    "api_key": "YOUR_API_KEY", # User should replace this
    "watched_coins": [
        # Example structure for a watched coin
        # {
        #     "symbol": "BTC", 
        #     "id": 1, # CoinMarketCap ID
        #     "name": "Bitcoin",
        #     "alert_above": null, 
        #     "alert_below": null,
        #     "alert_active": False
        # }
    ],
    "refresh_interval_seconds": 60,
    "sound_enabled": True
}

def load_config():
    """Loads the configuration from config.json.

    If the file doesn't exist, it creates it with default values.
    If the file is corrupted or not valid JSON, it attempts to return default config.

    Returns:
        dict: The configuration dictionary.
    """
    if not os.path.exists(CONFIG_FILE_PATH):
        print(f"Configuration file '{CONFIG_FILE_PATH}' not found. Creating with default values.")
        save_config(DEFAULT_CONFIG) # Save default config if file doesn't exist
        return DEFAULT_CONFIG.copy() # Return a copy to avoid modifying the global default
    
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            config = json.load(f)
            # Basic validation: check if essential keys are present, if not, merge with default
            # This handles cases where the config file might be partially corrupted or outdated
            updated = False
            for key, default_value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = default_value
                    updated = True
            if updated:
                print("Configuration file was missing some keys. Updated with defaults.")
                save_config(config) # Save the updated config
            return config
    except json.JSONDecodeError:
        print(f"Error decoding JSON from '{CONFIG_FILE_PATH}'. Using default configuration.")
        # Optionally, you could back up the corrupted file here before overwriting or returning default
        return DEFAULT_CONFIG.copy()
    except Exception as e:
        print(f"An unexpected error occurred while loading configuration: {e}. Using default configuration.")
        return DEFAULT_CONFIG.copy()

def save_config(config_data):
    """Saves the given configuration data to config.json.

    Args:
        config_data (dict): The configuration dictionary to save.
    """
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config_data, f, indent=4)
        # print(f"Configuration saved to '{CONFIG_FILE_PATH}'") # Can be too verbose
    except Exception as e:
        print(f"Error saving configuration to '{CONFIG_FILE_PATH}': {e}")

# --- Example Usage / Testing ---
if __name__ == '__main__':
    print(f"Config file expected at: {CONFIG_FILE_PATH}")

    # Test loading (and creating if not exists)
    print("\n--- Loading configuration ---")
    current_config = load_config()
    print("Current configuration loaded:")
    print(json.dumps(current_config, indent=4))

    # Test saving - modify a value and save
    print("\n--- Modifying and saving configuration ---")
    current_config["refresh_interval_seconds"] = 120
    if not current_config.get("watched_coins"):
        current_config["watched_coins"] = [] # Ensure it's a list if it was missing
    
    # Example of adding/updating a coin for testing
    # Ensure we don't add duplicates if this test is run multiple times
    test_coin_symbol = "TESTCOIN"
    if not any(c["symbol"] == test_coin_symbol for c in current_config["watched_coins"]):
        current_config["watched_coins"].append({
            "symbol": test_coin_symbol,
            "id": 9999, # Fictional ID for testing
            "name": "Test Coin",
            "alert_above": 100.0,
            "alert_below": 50.0,
            "alert_active": True
        })
        print(f"Added/Updated '{test_coin_symbol}' to watched_coins for testing.")
    else:
        print(f"'{test_coin_symbol}' already in watched_coins.")

    save_config(current_config)
    print("Configuration supposedly saved.")

    # Verify by loading again
    print("\n--- Reloading configuration to verify save ---")
    reloaded_config = load_config()
    print("Reloaded configuration:")
    print(json.dumps(reloaded_config, indent=4))

    if reloaded_config["refresh_interval_seconds"] == 120 and \
       any(c["symbol"] == test_coin_symbol for c in reloaded_config["watched_coins"]):
        print("\nTest successful: Configuration was modified, saved, and reloaded correctly.")
    else:
        print("\nTest failed: Configuration did not save or reload as expected.")

    # Clean up the test coin (optional)
    # current_config["watched_coins"] = [c for c in current_config["watched_coins"] if c["symbol"] != test_coin_symbol]
    # save_config(current_config)
    # print(f"Cleaned up {test_coin_symbol} from config.")    