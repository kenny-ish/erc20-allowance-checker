# erc20-allowance-checker

Lists which DeFi contracts can currently move an address's tokens. It only uses `eth_call`, so any
RPC works, including your own node.

```bash
python allowances.py 0xYourAddress
python allowances.py 0xYourAddress --token 0x... --spender 0x...     # add your own
python allowances.py 0xYourAddress --rpc http://localhost:8545
```

It checks a matrix of common tokens (USDC, USDT, WETH, DAI, WBTC, LINK, UNI) against well-known
spenders (Uniswap Permit2 and routers, Aave v3 Pool, Compound v3 USDC, Balancer Vault, 0x Exchange
Proxy, 1inch v5, OpenSea Conduit) and reads two kinds of approval:

1. ERC-20 allowances with `token.allowance(owner, spender)`.
2. Permit2 allowances. Once a token is approved to Permit2, other contracts can spend it through
   Permit2. `Permit2.allowance(owner, token, spender)` returns `(amount, expiration, nonce)`, and an
   entry with a non-zero amount that hasn't expired is still usable.

Only active entries are printed, and unlimited ones are marked. `--token` and `--spender` add more
contracts to the matrix and can be repeated.

Approvals to contracts outside the matrix won't show up. Finding those means scanning `Approval`
logs across every token contract, which public RPCs don't allow. For a specific contract you've used,
pass it with `--spender`.

## Tests

```bash
python -m unittest -v
```
