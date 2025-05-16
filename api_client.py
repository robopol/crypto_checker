import requests
import json
import os

# Base URL for the CoinMarketCap API v1. You might need to adjust if using a different version.
CMC_API_BASE_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency"

class CoinMarketCapAPI:
    def __init__(self, api_key):
        """Initializes the API client with the given API key.

        Args:
            api_key (str): Your CoinMarketCap API key.
        """
        self.api_key = api_key
        self.headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': self.api_key,
        }

    def get_quotes(self, symbols=None, ids=None):
        """Fetches the latest market quotes for one or more cryptocurrencies.

        You can specify cryptocurrencies by symbol or by CoinMarketCap ID.
        It's recommended to use IDs for more accuracy if available.

        Args:
            symbols (list, optional): A list of cryptocurrency symbols (e.g., ["BTC", "ETH"]).
            ids (list, optional): A list of CoinMarketCap IDs (e.g., [1, 1027]).

        Returns:
            dict: The API response (JSON decoded into a dictionary) or None if an error occurs.
                  Successful response structure (simplified):
                  {
                      "status": {
                          "timestamp": "2023-10-27T10:00:00.000Z",
                          "error_code": 0,
                          "error_message": null,
                          ...
                      },
                      "data": {
                          "BTC": { ... quote data ... },
                          "ETH": { ... quote data ... }
                          // or by ID if IDs were passed
                          "1": { ... quote data ... }
                      }
                  }
                  Error response structure (simplified):
                  {
                      "status": {
                          "timestamp": "2023-10-27T10:00:00.000Z",
                          "error_code": NNN,
                          "error_message": "Error description",
                          ...
                      },
                      "data": {}
                  }
        """
        if not symbols and not ids:
            # print("Error: Either symbols or ids must be provided to get_quotes.")
            return {"error": "Either symbols or ids must be provided.", "data": {}}

        params = {}
        if symbols:
            params['symbol'] = ",".join(symbols)
        elif ids:
            # Convert all IDs to string as the API expects comma-separated string of IDs
            params['id'] = ",".join(map(str, ids))

        try:
            response = requests.get(f"{CMC_API_BASE_URL}/quotes/latest", headers=self.headers, params=params)
            response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            # Try to parse the JSON error response from CMC if available
            try:
                error_data = response.json()
                error_message = error_data.get("status", {}).get("error_message", str(http_err))
                error_code = error_data.get("status", {}).get("error_code", "N/A")
                print(f"HTTP error occurred: {error_message} (Code: {error_code})")
                return {"error": error_message, "data": {}, "status_code": response.status_code, "error_details": error_data}
            except json.JSONDecodeError:
                print(f"HTTP error occurred: {http_err} (Status code: {response.status_code})")
                return {"error": str(http_err), "data": {}, "status_code": response.status_code}
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
            return {"error": str(req_err), "data": {}}
        except json.JSONDecodeError as json_err:
            print(f"JSON decoding error: {json_err}. Response content: {response.text[:200]}...") # Log part of the response
            return {"error": f"JSON decoding error: {json_err}", "data": {}}

    def get_coin_map(self, symbols=None, start=1, limit=100):
        """Fetches a map of cryptocurrencies to their CoinMarketCap IDs.
           This can be useful to find the ID of a coin if you only know its symbol.
           The free plan might have limitations on how many results are returned or if this endpoint is available.

        Args:
            symbols (list, optional): A list of cryptocurrency symbols to look up.
                                     If provided, the API will try to return only these symbols.
            start (int, optional): The starting number for pagination (1-indexed).
            limit (int, optional): The number of results to return (max usually 5000 for paid plans, less for free).

        Returns:
            dict: The API response or None if an error occurs.
                  Successful response includes a "data" list with coin mappings.
        """
        params = {
            'start': start,
            'limit': limit
        }
        if symbols:
            params['symbol'] = ",".join(symbols)

        try:
            response = requests.get(f"{CMC_API_BASE_URL}/map", headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as http_err:
            try:
                error_data = response.json()
                error_message = error_data.get("status", {}).get("error_message", str(http_err))
                print(f"HTTP error occurred while fetching coin map: {error_message}")
                return {"error": error_message, "data": [], "status_code": response.status_code, "error_details": error_data}
            except json.JSONDecodeError:
                print(f"HTTP error occurred while fetching coin map: {http_err}")
                return {"error": str(http_err), "data": [], "status_code": response.status_code}
        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred while fetching coin map: {req_err}")
            return {"error": str(req_err), "data": []}
        except json.JSONDecodeError as json_err:
            print(f"JSON decoding error for coin map: {json_err}. Response content: {response.text[:200]}...")
            return {"error": f"JSON decoding error: {json_err}", "data": []}

# --- Testing (Example Usage) ---
if __name__ == '__main__':
    # IMPORTANT: Replace "YOUR_API_KEY" with your actual CoinMarketCap API key.
    # It is recommended to load the API key from an environment variable or a config file in a real application.
    api_key_from_env = os.environ.get('CMC_PRO_API_KEY') 
    
    if not api_key_from_env:
        print("API Key not found in environment variable CMC_PRO_API_KEY.")
        # Try to load from config.json as a fallback for local testing
        try:
            # Assuming api_client.py is in 'crypto/' and config.json is also in 'crypto/'
            config_path = os.path.join(os.path.dirname(__file__), 'config.json')
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                    api_key_from_env = config_data.get('api_key')
                    if api_key_from_env and api_key_from_env != "YOUR_API_KEY":
                        print(f"Loaded API key from config.json: {api_key_from_env[:4]}...{api_key_from_env[-4:]}")
                    else:
                        api_key_from_env = None # Reset if it's the placeholder
            if not api_key_from_env:
                 print("API key not found or is placeholder in config.json.")
        except Exception as e:
            print(f"Error reading config.json for API key: {e}")

    if not api_key_from_env:
        print("Please set CMC_PRO_API_KEY environment variable or update config.json, or enter key manually below.")
        api_key_from_env = input("Enter your CoinMarketCap API Key: ").strip()
        if not api_key_from_env:
            print("No API key provided. Exiting test.")
            exit()

    client = CoinMarketCapAPI(api_key=api_key_from_env)

    print("\n--- Test 1: Get quotes for BTC and ETH by symbol ---")
    quotes_response = client.get_quotes(symbols=["BTC", "ETH"])
    if quotes_response and not quotes_response.get("error"):
        btc_data = quotes_response.get("data", {}).get("BTC")
        if btc_data and isinstance(btc_data, list):
            print(f"BTC Price: ${btc_data[0]['quote']['USD']['price']:.2f}")
        elif btc_data: # if data is not a list (older API versions or direct object)
             print(f"BTC Price: ${btc_data['quote']['USD']['price']:.2f}")
        else:
            print("BTC data not found or in unexpected format.")
        
        eth_data = quotes_response.get("data", {}).get("ETH")
        if eth_data and isinstance(eth_data, list):
            print(f"ETH Price: ${eth_data[0]['quote']['USD']['price']:.2f}")
        elif eth_data:
            print(f"ETH Price: ${eth_data['quote']['USD']['price']:.2f}")
        else:
            print("ETH data not found or in unexpected format.")
    else:
        print(f"Error fetching quotes: {quotes_response.get('error') if quotes_response else 'No response'}")

    print("\n--- Test 2: Get quotes for Dogecoin (ID 74) by ID ---")
    doge_response = client.get_quotes(ids=[74])
    if doge_response and not doge_response.get("error"):
        doge_data = doge_response.get("data", {}).get("74") # API returns data keyed by ID as a string
        if doge_data and isinstance(doge_data, list): # New API returns a list even for single symbol/id
            print(f"Dogecoin (ID 74) Price: ${doge_data[0]['quote']['USD']['price']:.2f}")
        elif doge_data: # Handle if it's a direct object (older or different API behavior)
             print(f"Dogecoin (ID 74) Price: ${doge_data['quote']['USD']['price']:.2f}")
        else:
            print("Dogecoin data not found or in unexpected format.")
    else:
        print(f"Error fetching Dogecoin quote: {doge_response.get('error') if doge_response else 'No response'}")

    print("\n--- Test 3: Get coin map (first 5 coins) ---")
    map_response = client.get_coin_map(limit=5)
    if map_response and not map_response.get("error"):
        if map_response.get("data"):
            for coin in map_response["data"]:
                print(f"ID: {coin['id']}, Name: {coin['name']}, Symbol: {coin['symbol']}")
        else:
            print("No data in coin map response.")
    else:
        print(f"Error fetching coin map: {map_response.get('error') if map_response else 'No response'}")

    print("\n--- Test 4: Get coin map for a specific symbol (e.g., LTC) ---")
    ltc_map_response = client.get_coin_map(symbols=["LTC"])
    if ltc_map_response and not ltc_map_response.get("error"):
        if ltc_map_response.get("data"):
            for coin in ltc_map_response["data"]:
                print(f"LTC - ID: {coin['id']}, Name: {coin['name']}, Symbol: {coin['symbol']}")
        else:
            print("No data for LTC in coin map response.")
    else:
        print(f"Error fetching LTC coin map: {ltc_map_response.get('error') if ltc_map_response else 'No response'}")

    print("\n--- Test 5: Error case - Invalid API Key (example, will likely fail unless your key is truly 'INVALID_KEY') ---")
    # This test is illustrative. You'd need to temporarily use an invalid key to see the error.
    # invalid_client = CoinMarketCapAPI(api_key="INVALID_KEY_FOR_TESTING")
    # error_quotes = invalid_client.get_quotes(symbols=["BTC"])
    # print(f"Response for invalid key: {error_quotes}")

    print("\n--- Test 6: Error case - Non-existent symbol ---")
    non_existent_response = client.get_quotes(symbols=["NONEXISTENTSYMBOL"])
    if non_existent_response and non_existent_response.get("error"):
        print(f"Response for non-existent symbol: {non_existent_response['error']}")
        # print(f"Full error response: {non_existent_response}") # For more details
    elif non_existent_response and not non_existent_response.get("data", {}).get("NONEXISTENTSYMBOL"):
        # Sometimes API returns success but no data for the specific symbol
        print("Response for non-existent symbol: Symbol not found (no data returned for it).")
    else:
        print(f"Unexpected response for non-existent symbol: {non_existent_response}")

    print("\n--- Test 7: Get coin map for BNB ---")
    bnb_map_response = client.get_coin_map(symbols=["BNB"])
    if bnb_map_response and not bnb_map_response.get("error"):
        if bnb_map_response.get("data"):
            found_bnb = False
            for coin in bnb_map_response["data"]:
                print(f"BNB Map - ID: {coin['id']}, Name: {coin['name']}, Symbol: {coin['symbol']}, Slug: {coin.get('slug')}")
                if coin['symbol'] == "BNB":
                    found_bnb = True
            if not found_bnb:
                print("BNB not found in map response data list, even if overall request was successful.")
        else:
            print("No data in BNB coin map response, though request might have been successful.")
    else:
        error_msg = bnb_map_response.get('error', 'Unknown error') if bnb_map_response else 'No response'
        error_details_status = bnb_map_response.get("error_details", {}).get("status", {})
        cmc_error_msg = error_details_status.get("error_message")
        cmc_error_code = error_details_status.get("error_code")
        if cmc_error_msg:
            print(f"Error fetching BNB coin map: {cmc_error_msg} (Code: {cmc_error_code})")
        else:
            print(f"Error fetching BNB coin map: {error_msg}")
        # print(f"Full response for BNB map error: {bnb_map_response}")

    # Also try fetching quotes directly for BNB again, to see the raw error if any
    print("\n--- Test 8: Get quotes for BNB by symbol (direct test) ---")
    bnb_quotes_response = client.get_quotes(symbols=["BNB"])
    if bnb_quotes_response and not bnb_quotes_response.get("error"):
        bnb_data = bnb_quotes_response.get("data", {}).get("BNB")
        if bnb_data and isinstance(bnb_data, list) and len(bnb_data) > 0:
            print(f"BNB Quote Price: ${bnb_data[0]['quote']['USD']['price']:.2f}")
            print(f"BNB CMC ID from quote: {bnb_data[0]['id']}")
        else:
            print("BNB data not found or in unexpected format in quotes response.")
            print(f"Full quotes response for BNB: {bnb_quotes_response}")
    else:
        error_msg = bnb_quotes_response.get('error', 'Unknown error') if bnb_quotes_response else 'No response'
        error_details_status = bnb_quotes_response.get("error_details", {}).get("status", {})
        cmc_error_msg = error_details_status.get("error_message")
        cmc_error_code = error_details_status.get("error_code")
        if cmc_error_msg:
            print(f"Error fetching BNB quote: {cmc_error_msg} (Code: {cmc_error_code})")
        else:
            print(f"Error fetching BNB quote: {error_msg}")
        # print(f"Full response for BNB quote error: {bnb_quotes_response}") 