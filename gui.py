import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import time
import os

from config_manager import load_config, save_config, DEFAULT_CONFIG
from api_client import CoinMarketCapAPI
from coingecko_client import CoinGeckoAPI
from alert_manager import AlertManager

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates

# Global variable for the API client instance, so it doesn't have to be created repeatedly
# or it can be passed as an argument
# api_client_instance = None # This was for CoinMarketCap, coingecko_client will be separate


class ApiKeyDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Enter API Key")
        self.geometry("400x170") # Adjusted height for potentially longer text
        self.transient(parent) # Show above the main window
        self.grab_set() # Block interaction with the main window

        self.api_key = None

        self.label = ctk.CTkLabel(self, text="Enter your CoinMarketCap API Key:")
        self.label.pack(pady=10)

        self.entry = ctk.CTkEntry(self, width=350)
        self.entry.pack(pady=5)

        self.submit_button = ctk.CTkButton(self, text="Save Key", command=self._submit_key)
        self.submit_button.pack(pady=10)
        
        self.protocol("WM_DELETE_WINDOW", self._on_close) # If the user closes the dialog

    def _submit_key(self):
        key = self.entry.get()
        if key:
            self.api_key = key
            self.destroy()
        else:
            messagebox.showwarning("Missing Key", "Please enter your API key.", parent=self)

    def _on_close(self):
        if messagebox.askyesno("Quit?", 
                               "API key is not provided. The application cannot fetch data without it.\nDo you want to quit the application?", parent=self):
            self.parent.quit_app() # Call the method to quit the main application
        # If the user chooses "No", the dialog remains open

    def get_key(self):
        self.wait_window() # Wait until the dialog is closed
        return self.api_key


class CoinRow(ctk.CTkFrame):
    def __init__(self, master, coin_config, app_callbacks):
        super().__init__(master, fg_color="transparent")
        self.coin_config = coin_config
        self.app_callbacks = app_callbacks # dict with callbacks: remove_coin, update_coin_alert, toggle_alert_active, show_chart

        self.symbol_label = ctk.CTkLabel(self, text=coin_config.get("symbol", "N/A"), width=60, anchor="w")
        self.symbol_label.grid(row=0, column=0, padx=5, pady=2, sticky="w")

        self.price_label = ctk.CTkLabel(self, text="Loading...", width=110, anchor="w")
        self.price_label.grid(row=0, column=1, padx=5, pady=2, sticky="w")
        
        self.change_24h_label = ctk.CTkLabel(self, text="-", width=70, anchor="w")
        self.change_24h_label.grid(row=0, column=2, padx=5, pady=2, sticky="w")

        self.alert_above_entry = ctk.CTkEntry(self, width=65)
        self.alert_above_entry.insert(0, str(coin_config.get("alert_above", "")))
        self.alert_above_entry.grid(row=0, column=3, padx=5, pady=2)
        self.alert_above_entry.bind("<FocusOut>", lambda e: self._update_alert_value("alert_above"))
        self.alert_above_entry.bind("<Return>", lambda e: self._update_alert_value("alert_above"))

        self.alert_below_entry = ctk.CTkEntry(self, width=65)
        self.alert_below_entry.insert(0, str(coin_config.get("alert_below", "")))
        self.alert_below_entry.grid(row=0, column=4, padx=5, pady=2)
        self.alert_below_entry.bind("<FocusOut>", lambda e: self._update_alert_value("alert_below"))
        self.alert_below_entry.bind("<Return>", lambda e: self._update_alert_value("alert_below"))

        self.alert_active_var = ctk.BooleanVar(value=coin_config.get("alert_active", False))
        self.alert_active_check = ctk.CTkCheckBox(self, text="Active", variable=self.alert_active_var,
                                                  command=self._toggle_alert_active, width=70)
        self.alert_active_check.grid(row=0, column=5, padx=5, pady=2)

        self.chart_button = ctk.CTkButton(self, text="Chart", width=60, 
                                           command=lambda: self.app_callbacks["show_chart"](self.coin_config["symbol"]))
        self.chart_button.grid(row=0, column=6, padx=5, pady=2)

        self.remove_button = ctk.CTkButton(self, text="X", width=30, command=self._remove_self)
        self.remove_button.grid(row=0, column=7, padx=5, pady=2)
        
        self.original_fg_color = self.cget("fg_color") 

    def _validate_float_or_empty(self, value_str):
        if not value_str: # Empty string is allowed (no alert)
            return None
        try:
            return float(value_str)
        except ValueError:
            return "invalid" # Special value for invalid input

    def _update_alert_value(self, alert_type):
        entry_widget = self.alert_above_entry if alert_type == "alert_above" else self.alert_below_entry
        new_value_str = entry_widget.get()
        
        validated_value = self._validate_float_or_empty(new_value_str)

        if validated_value == "invalid":
            messagebox.showerror("Input Error", f"Invalid value for alert: '{new_value_str}'.\nPlease enter a number or leave it empty.", parent=self.winfo_toplevel())
            original_value = self.coin_config.get(alert_type)
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, str(original_value) if original_value is not None else "")
            return

        if self.coin_config.get(alert_type) != validated_value:
            self.app_callbacks["update_coin_alert"](self.coin_config["symbol"], self.coin_config["id"], alert_type, validated_value)
            self.coin_config[alert_type] = validated_value

    def _toggle_alert_active(self):
        is_active = self.alert_active_var.get()
        self.app_callbacks["toggle_alert_active"](self.coin_config["symbol"], self.coin_config["id"], is_active)
        self.coin_config["alert_active"] = is_active

    def _remove_self(self):
        if messagebox.askyesno("Confirm", f"Are you sure you want to remove tracking for {self.coin_config['symbol']}?", parent=self.winfo_toplevel()):
            self.app_callbacks["remove_coin"](self.coin_config["symbol"], self.coin_config["id"])
            self.destroy()

    def update_data(self, price, change_24h):
        if price is not None:
            price_text = ""
            if 0 < price < 0.01:  # For prices between 0 (exclusive) and 0.01 (exclusive)
                price_text = f"${price:,.8f}" # Display up to 8 decimal places
            elif price == 0: # Exactly zero
                price_text = "$0.00"
            else:  # For prices >= 0.01
                price_text = f"${price:,.2f}"
            self.price_label.configure(text=price_text)
        else:
            self.price_label.configure(text="Error")

        if change_24h is not None:
            color = "green" if change_24h >= 0 else "red"
            self.change_24h_label.configure(text=f"{change_24h:+.2f}%", text_color=color)
        else:
            self.change_24h_label.configure(text="-", text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])
            
    def show_visual_alert(self, alert_type):
        target_color = "#A0FFA0" if alert_type == "above" else "#FFA0A0" # Light green / Light red
        self.configure(fg_color=target_color)

    def clear_visual_alert(self):
        self.configure(fg_color="transparent") # Assuming default is transparent or use self.original_fg_color if set at init


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Crypto Tracker")
        self.geometry("960x600") # Increased width to accommodate new Chart button and adjust overall layout

        self.config = load_config()
        self.cmc_api_client = None # Renamed from self.api_client for clarity
        self.coingecko_client = CoinGeckoAPI()
        self.alert_manager = AlertManager(
            gui_callback_visual_alert=self.handle_visual_alert,
            sound_enabled_check_callback=lambda: self.config.get("sound_enabled", True)
        )
        self.coin_rows = {} 
        self.data_fetch_thread = None
        self.stop_fetching_event = threading.Event()

        self._check_api_key()
        self._create_widgets()
        self._load_watched_coins_to_gui()

        if self.cmc_api_client: 
            self.start_data_fetching_loop()

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _check_api_key(self):
        if not self.config.get("api_key"):
            dialog = ApiKeyDialog(self)
            key = dialog.get_key()
            if key:
                self.config["api_key"] = key
                save_config(self.config)
                self.cmc_api_client = CoinMarketCapAPI(self.config["api_key"])
            else:
                self.quit_app() 
                return 
        else:
            self.cmc_api_client = CoinMarketCapAPI(self.config["api_key"])

    def _create_widgets(self):
        self.add_coin_frame = ctk.CTkFrame(self)
        self.add_coin_frame.pack(pady=10, padx=10, fill="x")

        ctk.CTkLabel(self.add_coin_frame, text="Add Cryptocurrency (symbol, e.g., BTC):").pack(side="left", padx=5)
        self.add_coin_entry = ctk.CTkEntry(self.add_coin_frame, width=100)
        self.add_coin_entry.pack(side="left", padx=5)
        self.add_coin_button = ctk.CTkButton(self.add_coin_frame, text="Add", command=self._add_coin_action)
        self.add_coin_button.pack(side="left", padx=5)
        self.add_coin_entry.bind("<Return>", lambda event: self._add_coin_action())

        self.header_frame = ctk.CTkFrame(self, fg_color="gray20")
        self.header_frame.pack(fill="x", padx=10, pady=(5,0))
        
        headers = ["Symbol", "Price (USD)", "Change 24h", "Alert Above", "Alert Below", "Active", "Chart", "Remove"]
        # Adjusted widths for potentially longer English headers or content, and new Chart column
        col_widths = [60, 110, 80, 75, 75, 70, 70, 50] 

        for i, header_text in enumerate(headers):
            label = ctk.CTkLabel(self.header_frame, text=header_text, width=col_widths[i], font=ctk.CTkFont(weight="bold"), text_color="white")
            label.grid(row=0, column=i, padx=5, pady=5, sticky="w")

        self.coins_scrollable_frame = ctk.CTkScrollableFrame(self, height=300)
        self.coins_scrollable_frame.pack(pady=5, padx=10, fill="both", expand=True)
        
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(pady=10, padx=10, fill="x")

        self.refresh_label = ctk.CTkLabel(self.bottom_frame, text="Refresh Interval (s):")
        self.refresh_label.pack(side="left", padx=(0,5))
        self.refresh_interval_entry = ctk.CTkEntry(self.bottom_frame, width=50)
        self.refresh_interval_entry.insert(0, str(self.config.get("refresh_interval_seconds", 60)))
        self.refresh_interval_entry.pack(side="left", padx=5)
        self.refresh_interval_entry.bind("<FocusOut>", self._update_refresh_interval)
        self.refresh_interval_entry.bind("<Return>", self._update_refresh_interval)

        self.sound_enabled_var = ctk.BooleanVar(value=self.config.get("sound_enabled", True))
        self.sound_check = ctk.CTkCheckBox(self.bottom_frame, text="Enable Sounds", variable=self.sound_enabled_var, command=self._toggle_sound_enabled)
        self.sound_check.pack(side="left", padx=10)
        
        self.status_label = ctk.CTkLabel(self.bottom_frame, text="Status: Initializing...", anchor="e")
        self.status_label.pack(side="right", padx=5, fill="x", expand=True)

    def _load_watched_coins_to_gui(self):
        for coin_id_str, row_widget in list(self.coin_rows.items()):
            row_widget.destroy()
        self.coin_rows.clear()

        valid_watched_coins = []
        for coin_conf in self.config.get("watched_coins", []):
            if isinstance(coin_conf, dict) and "id" in coin_conf and "symbol" in coin_conf:
                self._add_coin_row_to_gui(coin_conf)
                valid_watched_coins.append(coin_conf)
            else:
                print(f"[CONFIG_ERROR] Skipping invalid coin configuration: {coin_conf}")
        
        if len(valid_watched_coins) != len(self.config.get("watched_coins", [])):
            print("[CONFIG_UPDATE] Invalid entries found in coin configuration. Updating config file.")
            self.config["watched_coins"] = valid_watched_coins
            save_config(self.config)
            
    def _add_coin_row_to_gui(self, coin_config):
        if not isinstance(coin_config, dict) or "id" not in coin_config:
            print(f"[GUI_ERROR] Attempted to add invalid coin_config to GUI: {coin_config}")
            return None

        if coin_config["id"] in self.coin_rows:
            # print(f"Coin {coin_config['symbol']} (ID: {coin_config['id']}) is already in GUI.")
            return None # Indicate that row was not added if already exists

        callbacks = {
            "remove_coin": self._handle_remove_coin,
            "update_coin_alert": self._handle_update_coin_alert_value,
            "toggle_alert_active": self._handle_toggle_alert_active,
            "show_chart": self._show_price_chart
        }
        row = CoinRow(self.coins_scrollable_frame, coin_config, callbacks)
        row.pack(fill="x", pady=2, padx=2)
        self.coin_rows[coin_config["id"]] = row
        return row

    def _add_coin_action(self):
        symbol_to_add = self.add_coin_entry.get().upper().strip()
        if not symbol_to_add:
            messagebox.showwarning("Missing Symbol", "Please enter a cryptocurrency symbol.", parent=self)
            return

        if not self.cmc_api_client:
            messagebox.showerror("API Error", "API client is not initialized. Please check your API key.", parent=self)
            self.status_label.configure(text="Status: API Key Error.")
            return

        for existing_coin in self.config["watched_coins"]:
            if existing_coin["symbol"] == symbol_to_add:
                messagebox.showinfo("Information", f"Cryptocurrency {symbol_to_add} is already being tracked.", parent=self)
                self.add_coin_entry.delete(0, tk.END)
                return

        self.status_label.configure(text=f"Status: Fetching ID for {symbol_to_add}...")
        self.update_idletasks()

        response = self.cmc_api_client.get_quotes(symbols=[symbol_to_add])

        if not response:
            messagebox.showerror("API Error", f"Failed to get information for {symbol_to_add}: No response from API.", parent=self)
            self.status_label.configure(text=f"Status: API error (no response) while adding {symbol_to_add}.")
            return

        if response.get("error"):
            error_detail = response.get("error_details", {}).get("status", {}).get("error_message")
            msg = f"Failed to get information for {symbol_to_add}: {error_detail if error_detail else response['error']}"
            messagebox.showerror("API Error", msg, parent=self)
            self.status_label.configure(text=f"Status: API error while adding {symbol_to_add}.")
            return

        coin_data_map = response.get("data")
        if not coin_data_map:
            messagebox.showerror("API Error", f"Failed to get information for {symbol_to_add}: API response missing 'data' field.", parent=self)
            self.status_label.configure(text=f"Status: API error (missing data) for {symbol_to_add}.")
            return
        
        # Get the data for the specific symbol from the map
        # It might be a direct object or a list containing one object.
        data_for_symbol_entry = coin_data_map.get(symbol_to_add)
        coin_api_data = None

        if isinstance(data_for_symbol_entry, list):
            if len(data_for_symbol_entry) > 0:
                coin_api_data = data_for_symbol_entry[0] # Take the first element
        elif isinstance(data_for_symbol_entry, dict):
            coin_api_data = data_for_symbol_entry # It's a direct object

        if coin_api_data: 
            coin_id = coin_api_data.get("id")
            coin_name = coin_api_data.get("name")

            if coin_id is None:
                messagebox.showerror("API Error", f"Failed to get ID for symbol {symbol_to_add} from API response data structure.", parent=self)
                self.status_label.configure(text=f"Status: Error parsing ID for {symbol_to_add}.")
                return
            
            if any(c["id"] == coin_id for c in self.config["watched_coins"]):
                messagebox.showinfo("Information", f"Cryptocurrency {symbol_to_add} (ID: {coin_id}, Name: {coin_name}) is already being tracked.", parent=self)
                self.add_coin_entry.delete(0, tk.END)
                self.status_label.configure(text=f"Status: {symbol_to_add} is already tracked.")
                return

            new_coin_config = {
                "symbol": symbol_to_add,
                "id": coin_id,
                "name": coin_name,
                "alert_above": None, 
                "alert_below": None,
                "alert_active": False
            }
            self.config["watched_coins"].append(new_coin_config)
            save_config(self.config)
            
            new_row = self._add_coin_row_to_gui(new_coin_config)
            if new_row:
                self._fetch_data_once([new_coin_config])
            
            self.add_coin_entry.delete(0, tk.END)
            self.status_label.configure(text=f"Status: {symbol_to_add} ({coin_name}) added.")
        else:
            messagebox.showerror("Symbol Not Found", f"Cryptocurrency with symbol '{symbol_to_add}' was not found by CoinMarketCap, or the API returned no specific data for it in the expected format.", parent=self)
            self.status_label.configure(text=f"Status: Symbol {symbol_to_add} not found by API or data format issue.")

    def _handle_remove_coin(self, symbol, coin_id):
        self.config["watched_coins"] = [c for c in self.config["watched_coins"] if c["id"] != coin_id]
        save_config(self.config)
        
        if coin_id in self.coin_rows:
            del self.coin_rows[coin_id]
        
        self.alert_manager.reset_all_alerts_for_coin(symbol, coin_id)
        self.status_label.configure(text=f"Status: {symbol} removed.")

    def _handle_update_coin_alert_value(self, symbol, coin_id, alert_type, new_value):
        changed = False
        for coin_conf in self.config["watched_coins"]:
            if coin_conf["id"] == coin_id:
                if coin_conf.get(alert_type) != new_value:
                    old_value = coin_conf.get(alert_type)
                    if old_value is not None:
                         self.alert_manager.reset_alert_state(symbol, coin_id, alert_type.split('_')[1], old_value)
                    
                    coin_conf[alert_type] = new_value
                    changed = True
                    break
        if changed:
            save_config(self.config)
            self.status_label.configure(text=f"Status: Alert for {symbol} ({alert_type}) updated to {new_value if new_value is not None else 'none'}.")

    def _handle_toggle_alert_active(self, symbol, coin_id, is_active):
        changed = False
        for coin_conf in self.config["watched_coins"]:
            if coin_conf["id"] == coin_id:
                if coin_conf.get("alert_active") != is_active:
                    coin_conf["alert_active"] = is_active
                    changed = True
                    if not is_active:
                        self.alert_manager.reset_all_alerts_for_coin(symbol, coin_id)
                    break
        if changed:
            save_config(self.config)
            self.status_label.configure(text=f"Status: Alerts for {symbol} {'activated' if is_active else 'deactivated'}.")

    def _update_refresh_interval(self, event=None):
        try:
            new_interval = int(self.refresh_interval_entry.get())
            if new_interval >= 10:
                if self.config["refresh_interval_seconds"] != new_interval:
                    self.config["refresh_interval_seconds"] = new_interval
                    save_config(self.config)
                    self.status_label.configure(text=f"Status: Refresh interval set to {new_interval}s.")
                    self.stop_data_fetching_loop()
                    self.start_data_fetching_loop()
            else:
                messagebox.showwarning("Invalid Interval", "Refresh interval must be at least 10 seconds.", parent=self)
                self.refresh_interval_entry.delete(0, tk.END)
                self.refresh_interval_entry.insert(0, str(self.config["refresh_interval_seconds"]))
        except ValueError:
            messagebox.showerror("Input Error", "Invalid value for refresh interval. Please enter an integer.", parent=self)
            self.refresh_interval_entry.delete(0, tk.END)
            self.refresh_interval_entry.insert(0, str(self.config["refresh_interval_seconds"]))
        self.focus_set()

    def _toggle_sound_enabled(self):
        is_enabled = self.sound_enabled_var.get()
        if self.config.get("sound_enabled") != is_enabled:
            self.config["sound_enabled"] = is_enabled
            save_config(self.config)
            self.status_label.configure(text=f"Status: Sound alerts {'enabled' if is_enabled else 'disabled'}.")

    def _fetch_data_loop(self):
        print("Data fetching loop started.")
        while not self.stop_fetching_event.is_set():
            watched_coins_config = list(self.config.get("watched_coins", []))
            if not watched_coins_config:
                self.after(0, lambda: self.status_label.configure(text=f"Status: No coins to watch. Last act.: {time.strftime('%H:%M:%S')}"))
                # Wait for the refresh interval, but check for stop event periodically
                refresh_interval = self.config.get("refresh_interval_seconds", 60)
                for _ in range(refresh_interval):
                    if self.stop_fetching_event.is_set(): break
                    time.sleep(1)
                if self.stop_fetching_event.is_set(): break
                continue

            if not self.cmc_api_client:
                print("API client not available in fetch loop.")
                self.after(0, lambda: self.status_label.configure(text="Status: API Key Error. Fetching stopped."))
                break

            coin_ids_to_fetch = [c["id"] for c in watched_coins_config if c.get("id") is not None]
            
            if not coin_ids_to_fetch:
                refresh_interval = self.config.get("refresh_interval_seconds", 60)
                for _ in range(refresh_interval):
                    if self.stop_fetching_event.is_set(): break
                    time.sleep(1)
                if self.stop_fetching_event.is_set(): break
                continue

            self.after(0, lambda: self.status_label.configure(text=f"Status: Fetching data... ({len(coin_ids_to_fetch)} coins)"))
            
            api_response = self.cmc_api_client.get_quotes(ids=coin_ids_to_fetch)

            if self.stop_fetching_event.is_set(): break

            if api_response and api_response.get("data"):
                api_data = api_response["data"]
                all_updates_successful = True
                for coin_conf in watched_coins_config:
                    if self.stop_fetching_event.is_set(): break # Check before processing each coin
                    coin_id_str = str(coin_conf["id"])
                    coin_data_from_api = api_data.get(coin_id_str)

                    if coin_data_from_api:
                        try:
                            current_price = float(coin_data_from_api["quote"]["USD"]["price"])
                            change_24h = float(coin_data_from_api["quote"]["USD"]["percent_change_24h"])
                            
                            if self.stop_fetching_event.is_set(): break 
                            if coin_conf["id"] in self.coin_rows:
                                # Check if widget still exists before calling self.after
                                if self.coin_rows[coin_conf["id"]].winfo_exists():
                                    self.after(0, self.coin_rows[coin_conf["id"]].update_data, current_price, change_24h)
                            
                            self.alert_manager.check_and_trigger_alerts(
                                coin_conf["symbol"], coin_conf["id"], current_price, coin_conf
                            )
                        except (TypeError, ValueError, KeyError) as e:
                            print(f"Error processing data for {coin_conf['symbol']} (ID: {coin_conf['id']}): {e}. Data: {coin_data_from_api}")
                            if coin_conf["id"] in self.coin_rows:
                                if self.coin_rows[coin_conf["id"]].winfo_exists():
                                    self.after(0, self.coin_rows[coin_conf["id"]].update_data, None, None)
                            all_updates_successful = False
                    else:
                        if coin_conf["id"] in self.coin_rows:
                            if self.coin_rows[coin_conf["id"]].winfo_exists():
                                 self.after(0, self.coin_rows[coin_conf["id"]].update_data, None, None)
                        all_updates_successful = False
                if self.stop_fetching_event.is_set(): break
                
                if all_updates_successful:
                    if self.status_label.winfo_exists(): self.after(0, lambda: self.status_label.configure(text=f"Status: Data updated. Last act.: {time.strftime('%H:%M:%S')}"))
                else:
                    if self.status_label.winfo_exists(): self.after(0, lambda: self.status_label.configure(text=f"Status: Data partially updated (some errors). Last act.: {time.strftime('%H:%M:%S')}"))

            elif api_response and api_response.get("error"):
                error_msg = api_response.get("error")
                print(f"API Error in fetch loop: {error_msg}")
                if self.status_label.winfo_exists(): self.after(0, lambda: self.status_label.configure(text=f"Status: API Error: {error_msg}"))
                status_obj = api_response.get("error_details", {}).get("status", {})
                cmc_error_msg = status_obj.get("error_message", "")
                if "API key missing" in cmc_error_msg or \
                   "Invalid API key" in cmc_error_msg or \
                   "is not a valid UUID" in cmc_error_msg or \
                   "not a valid plan" in cmc_error_msg:
                    if self.status_label.winfo_exists(): 
                        self.after(0, self._prompt_for_api_key_again) 
                    break
            else:
                print("Unknown error or no data from API in fetch loop.")
                if self.status_label.winfo_exists(): self.after(0, lambda: self.status_label.configure(text=f"Status: Unknown API error. Last act.: {time.strftime('%H:%M:%S')}"))

            # Wait for the refresh interval, but check for stop event periodically
            refresh_interval = self.config.get("refresh_interval_seconds", 60)
            for _ in range(refresh_interval):
                if self.stop_fetching_event.is_set(): break
                time.sleep(1)
            # if self.stop_fetching_event.is_set(): break # This break is already handled by the loop's condition
        
        print("Data fetching loop stopped.")

    def _fetch_data_once(self, coins_to_fetch_config: list):
        if not self.cmc_api_client or not coins_to_fetch_config:
            return

        coin_ids = [c["id"] for c in coins_to_fetch_config if c.get("id") is not None]
        if not coin_ids: return

        self.status_label.configure(text=f"Status: Fetching data for new coins...")
        self.update_idletasks()
        
        api_response = self.cmc_api_client.get_quotes(ids=coin_ids)

        if api_response and api_response.get("data"):
            api_data = api_response["data"]
            for coin_conf in coins_to_fetch_config:
                coin_id_str = str(coin_conf["id"])
                coin_data_from_api = api_data.get(coin_id_str)
                if coin_data_from_api:
                    try:
                        current_price = float(coin_data_from_api["quote"]["USD"]["price"])
                        change_24h = float(coin_data_from_api["quote"]["USD"]["percent_change_24h"])
                        if coin_conf["id"] in self.coin_rows:
                            self.coin_rows[coin_conf["id"]].update_data(current_price, change_24h)
                    except (TypeError, ValueError, KeyError) as e:
                        print(f"Error during single fetch for {coin_conf['symbol']}: {e}")
                        if coin_conf["id"] in self.coin_rows:
                           self.coin_rows[coin_conf["id"]].update_data(None, None)
            self.status_label.configure(text=f"Status: Data for new coins fetched.")
        elif api_response and api_response.get("error"):
            self.status_label.configure(text=f"Status: API error fetching new coins: {api_response.get('error')}")
        else:
            self.status_label.configure(text=f"Status: Error fetching data for new coins.")

    def start_data_fetching_loop(self):
        if not self.cmc_api_client:
            print("Cannot start fetching loop: API client not initialized.")
            self.status_label.configure(text="Status: API key not set. Tracking not started.")
            return

        if self.data_fetch_thread is not None and self.data_fetch_thread.is_alive():
            # print("Data fetching loop already running.") # This can be noisy if called often
            return
            
        self.stop_fetching_event.clear()
        self.data_fetch_thread = threading.Thread(target=self._fetch_data_loop, daemon=True)
        self.data_fetch_thread.start()
        self.status_label.configure(text="Status: Tracking started.")

    def stop_data_fetching_loop(self):
        if self.data_fetch_thread is not None and self.data_fetch_thread.is_alive():
            print("Stopping data fetching loop...")
            self.stop_fetching_event.set()
            self.data_fetch_thread.join(timeout=5) 
            if self.data_fetch_thread.is_alive():
                print("Data fetching thread did not stop gracefully.")
            # else:
                # print("Data fetching loop stopped gracefully.") # Can be too verbose
        self.data_fetch_thread = None 

    def handle_visual_alert(self, symbol, message, alert_type):
        for coin_id, row in self.coin_rows.items():
            if row.coin_config["symbol"] == symbol:
                self.after(0, row.show_visual_alert, alert_type)
                # self.after(10000, lambda r=row: r.clear_visual_alert()) # Auto clear visual alert after 10s
                break

    def _prompt_for_api_key_again(self):
        messagebox.showerror("API Key Error", "Your API key is invalid, missing, or your plan does not allow access.\nPlease enter a valid key.", parent=self)
        self.config["api_key"] = None 
        save_config(self.config)
        self.cmc_api_client = None
        self.stop_data_fetching_loop()
        self._check_api_key() 
        if self.cmc_api_client:
            self.start_data_fetching_loop()

    def _show_price_chart(self, coin_symbol_cmc):
        """Displays a price chart for the given cryptocurrency symbol in a new window."""
        self.status_label.configure(text=f"Status: Fetching chart data for {coin_symbol_cmc}...")
        cg_id = self.coingecko_client.get_coin_id_by_symbol(coin_symbol_cmc)

        if not cg_id:
            messagebox.showerror("Chart Error", 
                                 f"Could not find CoinGecko ID for symbol '{coin_symbol_cmc}'.\n"+
                                 "Make sure the symbol is correct and listed on CoinGecko.",
                                 parent=self)
            self.status_label.configure(text=f"Status: Failed to get CoinGecko ID for {coin_symbol_cmc}.")
            return

        # Fetch data for the last 30 days as an example
        # User can choose other options like "1", "7", "90", "180", "365", "max"
        historical_data = self.coingecko_client.get_historical_market_data(cg_id, days="30")

        if not historical_data or not historical_data['timestamps'] or not historical_data['prices']:
            messagebox.showinfo("Chart Data Unavailable", 
                                f"Could not fetch or parse historical price data for {coin_symbol_cmc} ({cg_id}) from CoinGecko.",
                                parent=self)
            self.status_label.configure(text=f"Status: No historical data for {coin_symbol_cmc}.")
            return

        self.status_label.configure(text=f"Status: Displaying chart for {coin_symbol_cmc}.")

        chart_window = ctk.CTkToplevel(self)
        chart_window.title(f"Price Chart: {coin_symbol_cmc}")
        chart_window.geometry("800x600")
        chart_window.grab_set() # Keep focus

        try:
            fig = plt.figure(figsize=(7.5, 5.5), dpi=100)
            plot = fig.add_subplot(1, 1, 1)

            timestamps = historical_data['timestamps']
            prices = historical_data['prices']

            plot.plot(timestamps, prices, marker='.', linestyle='-', color='blue')
            
            # Formatting the x-axis to show dates nicely
            plot.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M')) # More detailed for shorter periods
            if (timestamps[-1] - timestamps[0]).days > 60:
                 plot.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            elif (timestamps[-1] - timestamps[0]).days > 2:
                 plot.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %Hh'))
            
            fig.autofmt_xdate() # Auto-rotate date labels

            plot.set_title(f"{coin_symbol_cmc} ({cg_id}) - Last 30 Days Price (USD)", fontsize=14)
            plot.set_xlabel("Date", fontsize=12)
            plot.set_ylabel("Price (USD)", fontsize=12)
            plot.grid(True)

            canvas = FigureCanvasTkAgg(fig, master=chart_window)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            canvas.draw()
        except Exception as e:
            print(f"Error creating chart: {e}")
            messagebox.showerror("Chart Display Error", f"Could not display the chart for {coin_symbol_cmc}:\n{e}", parent=chart_window)
            chart_window.destroy() # Close the chart window if an error occurs during plotting
            self.status_label.configure(text=f"Status: Error displaying chart for {coin_symbol_cmc}.")

    def quit_app(self):
        print("Quitting application...")
        self.stop_data_fetching_loop() # This sets the event and joins the thread.

        # Attempt to destroy any active Toplevel windows explicitly if we have references
        # For example, if self.chart_window holds a reference to an open chart:
        # if hasattr(self, 'chart_window') and self.chart_window and self.chart_window.winfo_exists():
        #     try:
        #         self.chart_window.destroy()
        #     except tk.TclError as e:
        #         print(f"Error destroying chart window: {e}")
        # self.chart_window = None # Clear reference

        # Stop the Tkinter mainloop. This should allow pending events to clear
        # and then the application to exit.
        self.quit() 
        # self.destroy() # Usually not needed after self.quit() and can cause errors.
                       # If the window doesn't close, it might be re-added, but this is a common
                       # point for "invalid command name" if Tkinter is already tearing down.

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you really want to quit Crypto Tracker?", parent=self):
            self.quit_app()

if __name__ == '__main__':
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    
    app = App()
    app.mainloop() 