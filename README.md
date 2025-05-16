# Crypto Portfolio Tracker & Alerter

A desktop application to track cryptocurrency prices, set price alerts, and view price history charts. It utilizes the CoinMarketCap API for live price data and CoinGecko API for historical chart data.


TODO:     
![Application Screenshot](screenshot.png) 


## Features

*   **Real-time Price Tracking:** Monitor prices of selected cryptocurrencies using the CoinMarketCap API.
*   **Historical Price Charts:** View price history charts for cryptocurrencies using the CoinGecko API, displayed using Matplotlib.
*   **Customizable Alerts:** Set upper and lower price limits for alerts.
*   **Audible & Visual Notifications:** Receive sound (requires a `.mp3` file) and visual notifications when price limits are reached.
*   **Persistent Configuration:** Saves API key, watched coins, alert settings, and refresh interval to `config.json`.
*   **User-Friendly GUI:** Modern graphical user interface built with `customtkinter`.
*   **Coin Management:** Easily add and remove cryptocurrencies from your watchlist.
*   **Adjustable Refresh Rate:** Set how often the data should be updated.
*   **Sound Control:** Globally enable or disable sound alerts.

## Technologies Used

*   **Python 3.7+**
*   **GUI:** `customtkinter`
*   **APIs:**
    *   CoinMarketCap API (for live prices)
    *   CoinGecko API (for historical price data for charts)
*   **HTTP Requests:** `requests`
*   **Sound Playback:** `pygame.mixer`
*   **Charting:** `matplotlib`
*   **Configuration:** JSON

## Prerequisites

*   Python 3.7 or newer.
*   A valid API key from [CoinMarketCap](https://pro.coinmarketcap.com/signup) (the free "Basic" plan should suffice for basic use).
    *   *Note: The CoinGecko API is used for chart data and generally does not require an API key for its free endpoints.*

## Setup & Installation

1.  **Clone the Repository or Download Project Files:**
    ```bash
    git clone https://your-repository-link.git
    cd crypto-tracker 
    ```

2.  **Create and Activate a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    Navigate to the project's `crypto/` directory (if you cloned a repo that already has this structure, or if your root is `crypto/`) and run:
    ```bash
    pip install -r crypto/requirements.txt
    ```

4.  **Obtain and Configure CoinMarketCap API Key:**
    *   To fully use the application and display current cryptocurrency prices, an API key from CoinMarketCap is required.
    *   **How to get a key:**
        1.  Visit the [CoinMarketCap API](https://coinmarketcap.com/api/) page.
        2.  Sign up or log in.
        3.  Choose the free "Basic" plan (or another according to your needs) and generate your API key.
    *   **Application Setup:**
        *   Upon first launch, the application will prompt you to enter your CoinMarketCap API key.
        *   This key will be stored in `crypto/config.json` within the application's directory. This file should not be shared or uploaded to public repositories (it's included in `.gitignore`).

5.  **Alert Sound File (Optional):**
    *   The application looks for an alert sound file named `allert.mp3` in the `assets/` subdirectory.
    *   If you wish to use sound alerts, place your custom `.mp3` file with this name at `crypto/assets/allert.mp3`.
    *   If the file is not found, sound alerts will be disabled, but the application will still run. A placeholder file might be created by `main.py` if `assets/` directory doesn't exist or `allert.mp3` is missing.

## Usage

1.  **Run the Application:**
    Execute the `main.py` script from within the `crypto/` directory:
    ```bash
    python main.py
    ```

2.  **Enter API Key:** If it's your first time, a dialog will ask for your CoinMarketCap API key. Enter it and save.

3.  **Adding a Cryptocurrency:**
    *   In the "Add Coin (Symbol)" field, type the symbol of the cryptocurrency (e.g., `BTC`, `ETH`, `PEPE`).
    *   Press the "Add" button or hit Enter.

4.  **Setting Alerts:**
    *   For each tracked coin, you can input numerical values in the "Alert Above" and "Alert Below" fields.
    *   Check the "Active" checkbox to enable alerts for that specific coin.
    *   Alert changes are saved automatically when you focus out of the input field or press Enter.

5.  **Removing a Cryptocurrency:**
    *   Click the "X" button in the row of the coin you want to remove.

6.  **Displaying Price Chart:**
    *   Click the "Chart" button in the row of the coin to view its price history in a new window.

7.  **Application Settings (Bottom Panel):**
    *   **Refresh Interval (s):** Set how often (in seconds) the data should update (minimum 10 seconds). Changes apply after focus out or Enter.
    *   **Enable Sounds:** A checkbox to globally enable or disable sound alerts.

8.  **Status Bar:**
    *   Displays the current application status, last data update time, and any errors.

## Project Structure

```
crypto/
├── main.py                 # Main script to launch the application
├── gui.py                  # GUI logic (CustomTkinter)
├── api_client.py           # Handles communication with CoinMarketCap API
├── coingecko_client.py     # Handles communication with CoinGecko API
├── config_manager.py       # Manages configuration (config.json)
├── alert_manager.py        # Handles alert logic and sound notifications
├── assets/                 # Contains resources like the alert sound
│   └── allert.mp3          # Default alert sound file
├── config.json             # Configuration file (auto-generated)
├── requirements.txt        # Project dependencies
├── README.md               # This file
└── PLAN.md                 # (Optional) Development plan document
```

## Troubleshooting

*   **Pygame Sound Issues:** If sound issues persist, ensure your system has the necessary audio codecs and drivers. `pygame` is generally more robust than `playsound` but can still encounter system-specific issues.
*   **API Key Limits:** The free CoinMarketCap API plan has request limits. Frequent refreshes or tracking many coins might lead to temporary rate limiting.
*   **Missing `allert.mp3`:** If `assets/allert.mp3` is missing, sound alerts will not function. The application might log a warning.

## Contributing

Contributions are welcome! Please feel free to submit a pull request or open an issue for bugs, feature requests, or improvements.

1.  Fork the Project
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4.  Push to the Branch (`git push origin feature/AmazingFeature`)
5.  Open a Pull Request

## License

Distributed under the MIT License. See `LICENSE` file for more information (if you add one).

## Author

[Ing. Robert Polak / Robopol] 

---

*This README was initially drafted with assistance from an AI programming partner.* 