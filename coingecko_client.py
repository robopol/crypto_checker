import requests
import time
import datetime # Added for timestamp conversion
import json

class CoinGeckoAPI:
    BASE_URL = "https://api.coingecko.com/api/v3"
    # Cache coin list for 1 hour to avoid frequent API calls for static data
    COIN_LIST_CACHE_DURATION = 3600 # seconds

    def __init__(self):
        """Initializes the CoinGecko API client."""
        self.coin_list_cache = None
        self.coin_list_last_updated = 0 # Timestamp of the last update

    def _fetch_coin_list(self):
        """Fetches the list of all coins from CoinGecko and caches it.
        Returns True if successful, False otherwise.
        """
        endpoint = f"{self.BASE_URL}/coins/list"
        try:
            response = requests.get(endpoint, timeout=10) # Added timeout
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            self.coin_list_cache = response.json()
            self.coin_list_last_updated = time.time()
            print(f"CoinGecko coin list fetched and cached. {len(self.coin_list_cache)} coins loaded.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error fetching CoinGecko coin list: {e}")
            self.coin_list_cache = None # Invalidate cache on error
            return False

    def get_coin_id_by_symbol(self, target_symbol):
        """Gets the CoinGecko ID for a given cryptocurrency symbol.

        Prioritizes direct matches and common mappings.

        Args:
            target_symbol (str): The cryptocurrency symbol (e.g., "BTC", "eth", "BNB").

        Returns:
            str: The CoinGecko ID (e.g., "bitcoin", "ethereum", "binancecoin") or None if not found or an error occurs.
        """
        current_time = time.time()
        if not self.coin_list_cache or (current_time - self.coin_list_last_updated > self.COIN_LIST_CACHE_DURATION):
            print("CoinGecko coin list cache is outdated or empty. Fetching fresh list...")
            if not self._fetch_coin_list():
                return None 

        if not self.coin_list_cache: 
             print("CoinGecko coin list is unexpectedly empty after fetch attempt.")
             return None

        target_symbol_lower = target_symbol.lower()
        target_symbol_upper = target_symbol.upper() # For cases like BNB matching name "BNB"

        # Priority 1: Hardcoded common symbols for accuracy
        if target_symbol_lower == "btc": return "bitcoin"
        if target_symbol_lower == "eth": return "ethereum"
        if target_symbol_lower == "bnb": return "binancecoin" # Added BNB
        if target_symbol_lower == "pepe": return "pepe"
        if target_symbol_lower == "shib": return "shiba-inu"
        # Consider adding more common symbols like ADA (cardano), SOL (solana), XRP (ripple), DOGE (dogecoin), DOT (polkadot), AVAX (avalanche-2), LTC (litecoin) etc.
        # if target_symbol_lower == "ada": return "cardano"
        # if target_symbol_lower == "sol": return "solana"
        # if target_symbol_lower == "xrp": return "ripple" 
        # if target_symbol_lower == "doge": return "dogecoin"

        # Priority 2: Symbol matches ID directly
        for coin in self.coin_list_cache:
            if coin.get('symbol') == target_symbol_lower and coin.get('id') == target_symbol_lower:
                # print(f"Exact match for symbol and id: {target_symbol_lower} -> {coin.get('id')}")
                return coin.get('id')

        # Priority 3: Collect all symbol matches and then apply heuristics
        potential_matches = []
        for coin in self.coin_list_cache:
            if coin.get('symbol') == target_symbol_lower:
                potential_matches.append(coin)
        
        if not potential_matches:
            print(f"CoinGecko ID for symbol '{target_symbol}' not found after all checks.")
            return None

        if len(potential_matches) == 1:
            # print(f"Single match for symbol: {target_symbol_lower} -> {potential_matches[0].get('id')}")
            return potential_matches[0].get('id')
        else:
            print(f"Multiple matches for symbol '{target_symbol_lower}': {[(c.get('id'), c.get('name')) for c in potential_matches]}")
            
            # Heuristic 3.1: Exact match of coin NAME with the (potentially uppercase) target symbol
            # This is good for symbols like "BNB" where the name is also "BNB"
            for coin in potential_matches:
                if coin.get('name') == target_symbol_upper or coin.get('name', '').lower() == target_symbol_lower:
                    print(f"Preferred match (name exact match '{target_symbol_upper}' or '{target_symbol_lower}'): {target_symbol_lower} -> {coin.get('id')}")
                    return coin.get('id')

            # Heuristic 3.2: Coin ID exactly matches a known pattern (like symbol, but for cases like bitcoin for btc)
            # This is somewhat covered by hardcoding but can be a generic rule if a symbol typically has a more verbose ID
            # Example: if we had a mapping like {"btc": "bitcoin"}, we could check if coin.get('id') == mapping[target_symbol_lower]
            # For now, this is mostly handled by hardcoding above.

            # Heuristic 3.3: Coin's ID contains the target_symbol_lower (e.g. symbol 'link', ID 'chainlink')
            # OR if the coin's name contains the target_symbol_lower and the symbol is a very close match to the start of the name.
            for coin in potential_matches:
                coin_id_lower = coin.get('id', '').lower()
                coin_name_lower = coin.get('name', '').lower()
                if target_symbol_lower == coin_id_lower: # e.g. symbol 'pepe', id 'pepe'
                    print(f"Preferred match (id exact match): {target_symbol_lower} -> {coin.get('id')}")
                    return coin.get('id')
                if target_symbol_lower in coin_id_lower and target_symbol_lower not in ["coin", "token"]: # Avoid generic matches
                    print(f"Preferred match (id contains symbol): {target_symbol_lower} -> {coin.get('id')}")
                    return coin.get('id')
            
            # Heuristic 3.4: Name contains symbol (more general)
            for coin in potential_matches:
                 coin_name_lower = coin.get('name', '').lower()
                 if target_symbol_lower in coin_name_lower and target_symbol_lower not in ["coin", "token"]:
                    print(f"Preferred match (name contains symbol): {target_symbol_lower} -> {coin.get('id')}")
                    return coin.get('id')

            # Fallback to the first one if no better heuristic confidently picked one
            print(f"Fallback to first of multiple matches after heuristics: {target_symbol_lower} -> {potential_matches[0].get('id')}")
            return potential_matches[0].get('id')

    def get_historical_market_data(self, coin_gecko_id, vs_currency="usd", days="7"):
        """Fetches historical market data for a given coin for a number of days.

        Args:
            coin_gecko_id (str): The CoinGecko ID of the coin (e.g., "bitcoin").
            vs_currency (str, optional): The target currency. Defaults to "usd".
            days (str, optional): Number of days of data (e.g., "1", "7", "30", "max"). Defaults to "7".

        Returns:
            dict: A dictionary with 'timestamps' and 'prices' lists, or None if an error occurs.
                  Example: {'timestamps': [datetime_obj1, ...], 'prices': [price1, ...]}
        """
        if not coin_gecko_id:
            print("Error: CoinGecko ID is required to fetch historical market data.")
            return None

        endpoint = f"{self.BASE_URL}/coins/{coin_gecko_id}/market_chart"
        params = {
            'vs_currency': vs_currency.lower(),
            'days': days
        }
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'prices' not in data or not isinstance(data['prices'], list):
                print(f"Historical price data not found or in unexpected format for {coin_gecko_id}.")
                return None

            timestamps = []
            prices = []
            for entry in data['prices']:
                if isinstance(entry, list) and len(entry) == 2:
                    # Convert timestamp from milliseconds to datetime object
                    try:
                        ts = datetime.datetime.fromtimestamp(entry[0] / 1000)
                        timestamps.append(ts)
                        prices.append(float(entry[1]))
                    except (ValueError, TypeError) as e:
                        print(f"Skipping invalid data point in historical data for {coin_gecko_id}: {entry} - Error: {e}")
                else:
                    print(f"Skipping malformed data point in historical data for {coin_gecko_id}: {entry}")
            
            if not timestamps or not prices:
                print(f"No valid historical data points processed for {coin_gecko_id}.")
                return None
                
            return {"timestamps": timestamps, "prices": prices}
        
        except requests.exceptions.RequestException as e:
            print(f"Error fetching historical market data for {coin_gecko_id}: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON for historical market data of {coin_gecko_id}: {e}")
            return None
        except Exception as e: # Catch any other unexpected errors
            print(f"An unexpected error occurred while fetching historical data for {coin_gecko_id}: {e}")
            return None

if __name__ == '__main__':
    client = CoinGeckoAPI()
    print("CoinGeckoAPI client initialized.")

    # Test get_coin_id_by_symbol
    print("\n--- Testing get_coin_id_by_symbol ---")
    btc_cg_id = client.get_coin_id_by_symbol("BTC")
    print(f"ID for BTC: {btc_cg_id}") # Expected: bitcoin

    eth_cg_id = client.get_coin_id_by_symbol("eth")
    print(f"ID for ETH: {eth_cg_id}") # Expected: ethereum

    non_existent_id = client.get_coin_id_by_symbol("NONEXISTENTTOKEN")
    print(f"ID for NONEXISTENTTOKEN: {non_existent_id}") # Expected: None

    # Test caching - second call should use cache if within COIN_LIST_CACHE_DURATION
    print("\n--- Testing cache for get_coin_id_by_symbol (should use cache) ---")
    btc_id_cached = client.get_coin_id_by_symbol("BTC")
    print(f"ID for BTC (cached): {btc_id_cached}") 

    # Test get_historical_market_data
    print("\n--- Testing get_historical_market_data for Bitcoin (last 7 days) ---")
    if btc_cg_id:
        historical_data_btc = client.get_historical_market_data(btc_cg_id, days="7")
        if historical_data_btc and historical_data_btc['timestamps'] and historical_data_btc['prices']:
            print(f"Fetched {len(historical_data_btc['prices'])} data points for BTC.")
            print(f"First timestamp: {historical_data_btc['timestamps'][0]}, Price: {historical_data_btc['prices'][0]}")
            print(f"Last timestamp: {historical_data_btc['timestamps'][-1]}, Price: {historical_data_btc['prices'][-1]}")
        else:
            print("Could not fetch historical data for BTC or data was empty.")
    else:
        print("Skipping historical data test for BTC as its CoinGecko ID was not found.")

    print("\n--- Testing get_historical_market_data for a non-existent CoinGecko ID ---")
    invalid_historical_data = client.get_historical_market_data("non-existent-coingecko-id")
    if invalid_historical_data is None:
        print("Correctly returned None for a non-existent CoinGecko ID.")
    else:
        print(f"Unexpectedly received data for non-existent CoinGecko ID: {invalid_historical_data}")

    print("\n--- Testing get_historical_market_data with days=\"1\" for Ethereum ---")
    if eth_cg_id:
        historical_data_eth_1d = client.get_historical_market_data(eth_cg_id, days="1")
        if historical_data_eth_1d and historical_data_eth_1d['timestamps'] and historical_data_eth_1d['prices']:
            print(f"Fetched {len(historical_data_eth_1d['prices'])} data points for ETH (1 day).")
            # print(f"Sample: {historical_data_eth_1d['timestamps'][0]} - {historical_data_eth_1d['prices'][0]}")
        else:
            print("Could not fetch 1-day historical data for ETH or data was empty.")
    else:
        print("Skipping 1-day historical data test for ETH as its CoinGecko ID was not found.") 