"""
Blockchain Explorer Tool Adapter.
Queries real-time blockchain data from mempool.space APIs.
"""

import hashlib
import requests
from backend.tools import registry

HASH_ALGORITHMS = {
    "sha256": hashlib.sha256,
    "sha512": hashlib.sha512,
    "md5": hashlib.md5,
    "blake2b": hashlib.blake2b,
}


def explore_block(block_height: str = "latest") -> str:
    """Get information about a Bitcoin block using mempool.space API."""
    try:
        block_height_str = str(block_height).strip()
        
        # Check if block_height looks like a block hash (64 hex characters)
        if len(block_height_str) == 64 and all(c in "0123456789abcdefABCDEF" for c in block_height_str):
            block_hash = block_height_str
        elif block_height_str.lower() == "latest":
            # Get latest height
            r = requests.get("https://mempool.space/api/blocks/tip/height", timeout=5)
            if r.status_code != 200:
                return "Error: Could not fetch latest block height."
            height = r.text.strip()
            # Get block hash
            r_hash = requests.get(f"https://mempool.space/api/block-height/{height}", timeout=5)
            if r_hash.status_code != 200:
                return f"Error: Block height '{height}' not found or API error."
            block_hash = r_hash.text.strip()
        else:
            height = str(int(block_height_str))
            # Get block hash
            r_hash = requests.get(f"https://mempool.space/api/block-height/{height}", timeout=5)
            if r_hash.status_code != 200:
                return f"Error: Block height '{height}' not found or API error."
            block_hash = r_hash.text.strip()

        # Get block details
        r_details = requests.get(f"https://mempool.space/api/v1/block/{block_hash}", timeout=5)
        if r_details.status_code != 200:
            return f"Error: Could not retrieve details for block hash {block_hash}."
        
        data = r_details.json()
        extras = data.get("extras", {})
        pool_info = extras.get("pool", {})
        miner_name = pool_info.get("name", "Unknown/Solo Miner")
        
        # Compute block reward in BTC (subsidy + fees)
        reward_sats = extras.get("reward", 0)
        reward_btc = reward_sats / 100_000_000 if reward_sats else (data.get("reward", 0) / 100_000_000)
        
        size_mb = data.get("size", 0) / (1024 * 1024)

        return (
            f"⛓️ Bitcoin Block #{data.get('height')}\n"
            f"  Hash: {data.get('id')}\n"
            f"  Transactions: {data.get('tx_count', 0):,}\n"
            f"  Size: {size_mb:.2f} MB\n"
            f"  Miner: {miner_name}\n"
            f"  Block Reward: {reward_btc:.4f} BTC\n"
            f"  Timestamp: {data.get('timestamp')}"
        )
    except Exception as e:
        return f"Error exploring block: {str(e)}"


def hash_data(data: str = "", algorithm: str = "sha256") -> str:
    """Hash data using various cryptographic algorithms."""
    if not data:
        return "Error: No data provided."
    algo = algorithm.lower().strip()
    if algo not in HASH_ALGORITHMS:
        return f"Error: Unknown algorithm '{algo}'. Available: {', '.join(HASH_ALGORITHMS.keys())}"
    h = HASH_ALGORITHMS[algo](data.encode()).hexdigest()
    return f"Algorithm: {algo.upper()}\nInput: {data[:100]}{'...' if len(data) > 100 else ''}\nHash: {h}"


def mining_stats() -> str:
    """Get real live Bitcoin mining statistics from mempool.space."""
    try:
        # 1. Get difficulty adjustment info
        r_diff = requests.get("https://mempool.space/api/v1/difficulty-adjustment", timeout=5)
        diff_data = r_diff.json() if r_diff.status_code == 200 else {}
        
        # 2. Get current hashrate and difficulty
        r_hash = requests.get("https://mempool.space/api/v1/mining/hashrate/3d", timeout=5)
        hash_data = r_hash.json() if r_hash.status_code == 200 else {}

        # 3. Get pool shares (1 week)
        r_pools = requests.get("https://mempool.space/api/v1/mining/pools/1w", timeout=5)
        pool_list = r_pools.json().get("pools", [])[:6] if r_pools.status_code == 200 else []

        # Parse hashrate to Exahashes/sec
        raw_hashrate = hash_data.get("currentHashrate", 0)
        hashrate_ehs = raw_hashrate / 1e18 if raw_hashrate else 0
        
        # Parse difficulty to Terahashes (T)
        raw_diff = hash_data.get("currentDifficulty", 0)
        diff_t = raw_diff / 1e12 if raw_diff else 0

        # Estimate difficulty change direction
        change_pct = diff_data.get("difficultyChange", 0)
        direction = "📈" if change_pct >= 0 else "📉"
        
        # Calculate days remaining for retarget
        rem_ms = diff_data.get("remainingTime", 0)
        rem_days = rem_ms / (1000 * 60 * 60 * 24)

        stats = {
            "Network Hashrate": f"{hashrate_ehs:.2f} EH/s",
            "Current Difficulty": f"{diff_t:.2f} T",
            "Difficulty Change": f"{direction} {change_pct:+.2f}%",
            "Remaining Blocks": f"{diff_data.get('remainingBlocks', 0)}",
            "Est. Retarget In": f"{rem_days:.1f} days",
            "Retarget Progress": f"{diff_data.get('progressPercent', 0):.1f}%",
        }

        lines = ["⛏️ Bitcoin Mining Statistics (Live Data):"]
        for k, v in stats.items():
            lines.append(f"  {k}: {v}")
            
        if pool_list:
            lines.append("\nTop Mining Pools (1 Week share):")
            total_blocks = sum(p.get("blockCount", 0) for p in pool_list)
            for p in pool_list:
                name = p.get("name", "Unknown")
                count = p.get("blockCount", 0)
                share = (count / total_blocks * 100) if total_blocks else 0
                bar = "█" * int(share / 2) + "░" * (15 - int(share / 2))
                lines.append(f"  {name:14s} {bar} {share:.1f}% ({count} blocks)")
        
        return "\n".join(lines)
    except Exception as e:
        return f"Error retrieving mining statistics: {str(e)}"


registry.register(
    name="explore_block", description="Get details about a Bitcoin block (hash, transaction count, size, miner/mining pool, block reward, timestamp) by height or 'latest'.",
    category="blockchain",
    parameters=[{"name": "block_height", "type": "string", "description": "Block height number (e.g. 845230) or 'latest' to get the latest block"}],
    examples=["Show me the latest Bitcoin block", "Block #845231"],
    handler=explore_block,
)


registry.register(
    name="hash_data", description="Hash data using SHA-256, SHA-512, MD5, or BLAKE2b.",
    category="blockchain",
    parameters=[
        {"name": "data", "type": "string", "description": "Data to hash"},
        {"name": "algorithm", "type": "string", "description": "Hash algorithm (sha256, sha512, md5, blake2b)"},
    ],
    examples=["Hash 'hello world' with SHA-256"],
    handler=hash_data,
)

registry.register(
    name="mining_stats", description="Get Bitcoin mining statistics including hashrate, difficulty, and top mining pools.",
    category="blockchain", parameters=[],
    examples=["Show mining stats", "Bitcoin mining overview"],
    handler=mining_stats,
)

