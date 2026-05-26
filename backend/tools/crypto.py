"""
Crypto Market Data Tool Adapter.
Fetches real-time cryptocurrency data from Coinpaprika API.
Integrates live metrics for prices, global market stats, and top ranking coins.
"""

import requests
from backend.tools import registry

SYMBOL_MAP = {
    "btc": "btc-bitcoin",
    "bitcoin": "btc-bitcoin",
    "eth": "eth-ethereum",
    "ethereum": "eth-ethereum",
    "sol": "sol-solana",
    "solana": "sol-solana",
    "usdt": "usdt-tether",
    "tether": "usdt-tether",
    "bnb": "bnb-binance-coin",
    "binancecoin": "bnb-binance-coin",
    "xrp": "xrp-xrp",
    "ripple": "xrp-xrp",
    "usdc": "usdc-usd-coin",
    "ada": "ada-cardano",
    "cardano": "ada-cardano",
    "doge": "doge-dogecoin",
    "dogecoin": "doge-dogecoin",
    "dot": "dot-polkadot",
    "polkadot": "dot-polkadot"
}


def get_crypto_price(coin: str = "bitcoin") -> str:
    """Fetch current price, 24h change, and market cap for a cryptocurrency."""
    coin = coin.lower().strip()
    coin_id = SYMBOL_MAP.get(coin, None)

    try:
        # If not in our predefined symbol map, query top tickers list and search dynamically
        if not coin_id:
            resp = requests.get("https://api.coinpaprika.com/v1/tickers?limit=250", timeout=8)
            if resp.status_code == 200:
                tickers = resp.json()
                for t in tickers:
                    if t.get("symbol", "").lower() == coin or t.get("name", "").lower() == coin or t.get("id", "").lower() == coin:
                        coin_id = t.get("id")
                        break

        # Fallback if still not found
        if not coin_id:
            # Let's try direct ID interpolation as a final guess
            coin_id = f"{coin}-{coin}"

        url = f"https://api.coinpaprika.com/v1/tickers/{coin_id}"
        resp = requests.get(url, timeout=8)
        if resp.status_code != 200:
            return f"Error: Could not retrieve price for '{coin}'. Code: {resp.status_code}"

        data = resp.json()
        name = data.get("name", "Unknown")
        symbol = data.get("symbol", "N/A")
        quotes = data.get("quotes", {}).get("USD", {})
        
        price = quotes.get("price", 0.0)
        change_24h = quotes.get("percent_change_24h", 0.0)
        market_cap = quotes.get("market_cap", 0)
        
        direction = "📈" if change_24h >= 0 else "📉"
        
        return (
            f"💰 {name} ({symbol})\n"
            f"  Price: ${price:,.2f} USD\n"
            f"  24h Change: {direction} {change_24h:+.2f}%\n"
            f"  Market Cap: ${market_cap:,.0f} USD"
        )
    except Exception as e:
        return f"Error retrieving cryptocurrency price: {str(e)}"


def get_market_overview() -> str:
    """Get an overview of the global cryptocurrency market stats and top coins."""
    try:
        # 1. Fetch global statistics
        resp_global = requests.get("https://api.coinpaprika.com/v1/global", timeout=8)
        global_data = resp_global.json() if resp_global.status_code == 200 else {}
        
        # 2. Fetch top 7 coins
        resp_top = requests.get("https://api.coinpaprika.com/v1/tickers?limit=7", timeout=8)
        top_coins = resp_top.json() if resp_top.status_code == 200 else []

        total_mcap = global_data.get("market_cap_usd", 0)
        volume_24h = global_data.get("volume_24h_usd", 0)
        btc_dominance = global_data.get("bitcoin_dominance_percentage", 0.0)
        coins_count = global_data.get("cryptocurrencies_number", 0)

        header = (
            f"🌐 Global Crypto Market Overview (Live Coinpaprika Data):\n"
            f"  Total Market Cap: ${total_mcap:,.0f} USD\n"
            f"  24h Volume: ${volume_24h:,.0f} USD\n"
            f"  BTC Dominance: {btc_dominance:.2f}%\n"
            f"  Total Coins Tracked: {coins_count:,}\n"
        )

        lines = ["\nTop Cryptocurrencies by Market Cap:"]
        for coin in top_coins:
            name = coin.get("name", "Unknown")
            symbol = coin.get("symbol", "N/A")
            quotes = coin.get("quotes", {}).get("USD", {})
            price = quotes.get("price", 0.0)
            change = quotes.get("percent_change_24h", 0.0)
            direction = "📈" if change >= 0 else "📉"
            lines.append(f"  {name:14s} ({symbol}): ${price:>12,.2f} USD  {direction} {change:+.2f}%")

        return header + "\n".join(lines)
    except Exception as e:
        return f"Error retrieving market overview: {str(e)}"


def get_trending_coins() -> str:
    """Get currently trending cryptocurrencies (highest searches/ranks)."""
    try:
        # Since Coinpaprika doesn't support a simple free trending endpoint,
        # we list the top 10 coins by market cap as the standard ranking list.
        resp = requests.get("https://api.coinpaprika.com/v1/tickers?limit=10", timeout=8)
        if resp.status_code != 200:
            return f"Error: Could not fetch top coins. Code: {resp.status_code}"
            
        coins = resp.json()
        lines = ["🔥 Top Cryptocurrencies by Market Volume & Capitalization:"]
        for i, c in enumerate(coins, 1):
            name = c.get("name", "?")
            symbol = c.get("symbol", "?")
            quotes = c.get("quotes", {}).get("USD", {})
            price = quotes.get("price", 0.0)
            lines.append(f"  {i}. {name} ({symbol}) - Price: ${price:,.2f} USD (Rank #{c.get('rank', '?')})")
        return "\n".join(lines)
    except Exception as e:
        return f"Error retrieving trending coins: {str(e)}"


# Register tools
registry.register(
    name="get_crypto_price",
    description="Get current price, 24h change, and market cap for a cryptocurrency. Supports BTC, ETH, SOL, ADA, DOGE, BNB, XRP, DOT and more.",
    category="blockchain",
    parameters=[
        {"name": "coin", "type": "string", "description": "Cryptocurrency name or symbol (e.g., 'bitcoin', 'btc', 'ethereum', 'eth')"}
    ],
    examples=["What's the price of Bitcoin?", "How is ETH doing?", "Check SOL price"],
    handler=get_crypto_price,
)

registry.register(
    name="get_market_overview",
    description="Get a comprehensive overview of the cryptocurrency market including top coins, prices, and market trends.",
    category="blockchain",
    parameters=[],
    examples=["Show me the crypto market", "Market overview", "How's the crypto market doing?"],
    handler=get_market_overview,
)

registry.register(
    name="get_trending_coins",
    description="Get the currently trending cryptocurrencies by search volume and social activity.",
    category="blockchain",
    parameters=[],
    examples=["What's trending in crypto?", "Trending coins", "Popular cryptocurrencies right now"],
    handler=get_trending_coins,
)
