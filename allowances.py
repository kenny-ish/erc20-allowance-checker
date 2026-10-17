"""Check ERC-20 and Permit2 allowances with eth_call only."""
import argparse
import json
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PERMIT2 = "0x000000000022D473030F116dDEE9F6B43aC78BA3"
TOKENS = {
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "LINK": "0x514910771AF9Ca656af840dff83E8264EcF986CA",
    "UNI": "0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984",
}
SPENDERS = {
    PERMIT2: "Uniswap Permit2",
    "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D": "Uniswap V2 Router",
    "0xE592427A0AEce92De3Edee1F18E0157C05861564": "Uniswap V3 SwapRouter",
    "0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45": "Uniswap SwapRouter02",
    "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2": "Aave v3 Pool",
    "0xc3d688B66703497DAA19211EEdff47f25384cdc3": "Compound v3 USDC",
    "0xBA12222222228d8Ba445958a75a0704d566BF2C8": "Balancer Vault",
    "0xDef1C0ded9bec7F1a1670819833240f027b25EfF": "0x Exchange Proxy",
    "0x1111111254EEB25477B68fb85Ed929f73A960582": "1inch v5 Router",
    "0x1E0049783F008A0085193E00003D00cd54003c71": "OpenSea Conduit",
}
ALLOWANCE = "0xdd62ed3e"  # allowance(address,address)
PERMIT2_ALLOWANCE = "0x927da105"  # allowance(address,address,address)
DECIMALS = "0x313ce567"
UNLIMITED = 2**255
UINT96_MAX = 2**96 - 1
UINT160_MAX = 2**160 - 1


def call(url, to, data):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": to, "data": data}, "latest"]}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "erc20-allowance-checker"})
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.load(r)
    if "error" in resp:
        raise RuntimeError(resp["error"].get("message"))
    return resp["result"]


def word(addr):
    return addr.lower()[2:].rjust(64, "0")


def decode_permit2(hexdata):
    """(amount uint160, expiration uint48, nonce uint48)."""
    d = hexdata[2:]
    return int(d[0:64], 16), int(d[64:128], 16), int(d[128:192], 16)


def is_unlimited(amount, cap=UNLIMITED):
    return amount >= cap or (cap == UNLIMITED and amount == UINT96_MAX)


def fmt(amount, decimals, cap=UNLIMITED):
    if is_unlimited(amount, cap):
        return "UNLIMITED"
    return f"{amount / 10 ** decimals:,.4f}"


def live_permit2(amount, expiration, now):
    return amount > 0 and expiration > now


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("owner")
    ap.add_argument("--rpc", default="https://ethereum-rpc.publicnode.com")
    ap.add_argument("--token", action="append", default=[], help="extra token address")
    ap.add_argument("--spender", action="append", default=[], help="extra spender address")
    a = ap.parse_args()
    tokens = dict(TOKENS, **{t[:10]: t for t in a.token})  # label -> address
    spenders = dict(SPENDERS, **{s: "custom" for s in a.spender})  # address -> label
    owner = word(a.owner)

    def erc20_allowance(pair):
        label, spender = pair
        return int(call(a.rpc, tokens[label], ALLOWANCE + owner + word(spender)) or "0x0", 16)

    def permit2_allowance(pair):
        label, spender = pair
        return decode_permit2(call(a.rpc, PERMIT2, PERMIT2_ALLOWANCE + owner + word(tokens[label]) + word(spender)))

    pairs = [(t, s) for t in tokens for s in spenders]
    p2_pairs = [(t, s) for t in tokens for s in spenders if s != PERMIT2]
    with ThreadPoolExecutor(max_workers=8) as pool:
        decimals = dict(zip(tokens, pool.map(lambda t: int(call(a.rpc, tokens[t], DECIMALS), 16), tokens)))
        erc20 = list(pool.map(erc20_allowance, pairs))
        permit2 = list(pool.map(permit2_allowance, p2_pairs))

    now = int(time.time())
    print(f"ERC-20 allowances of {a.owner}  ({len(pairs)} token x spender pairs checked)")
    live = [(p, v) for p, v in zip(pairs, erc20) if v > 0]
    for (t, s), v in sorted(live, key=lambda x: -x[1]):
        print(f"  {t:<10}{fmt(v, decimals[t]):>22}  -> {spenders[s]} ({s})")
    if not live:
        print("  none")

    print("\nPermit2 allowances (spend through Permit2)")
    live2 = [(p, v) for p, v in zip(p2_pairs, permit2) if live_permit2(v[0], v[1], now)]
    for (t, s), (amount, exp, _) in live2:
        days = (exp - now) / 86400
        print(f"  {t:<10}{fmt(amount, decimals[t], UINT160_MAX):>22}  -> {spenders[s]} ({s}), expires in {days:.1f} days")
    if not live2:
        print("  none")
    unlimited = sum(is_unlimited(v) for _, v in live)
    print(f"\n{len(live)} ERC-20 allowances ({unlimited} unlimited), {len(live2)} live Permit2 allowances")


if __name__ == "__main__":
    main()
