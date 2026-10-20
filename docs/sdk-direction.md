# Unified Python SDK scope

This local package provides public reads, CLOB order workflows, and Deposit Wallet relayer transactions on Polygon mainnet. It is not yet ready for live trading.

- Chain ID 137, Circle USDC, and verified Conditional Tokens and exchange contracts.
- Deposit Wallet maker and signer, signature type 3, and `CTF Exchange` EIP-712 version 2.
- CLOB API key owns orders; builder credentials authorize relayer submissions separately.
- Relayer supports `WALLET` and `WALLET-CREATE`; Safe and Proxy submissions are rejected.
- Position-backed V3 orders, combo RFQ, and protocol V2 collateral return are rejected before network requests.
- `configured_environment` requires explicit HTTPS/WSS service endpoints and Polygon RPC. Defaults are unconfigured.

The distribution is `kuest-sdk` and the import is `market_sdk`. Direct GitHub
checkouts require explicit endpoints. Operator ZIPs may add the existing
`.sdk/site-config.json` overlay for builder attribution, geoblocking, order
metadata, and site-scoped market discovery; presentation is set by the downloader.

Source: [Polymarket/py-sdk](https://github.com/Polymarket/py-sdk) at the revision in [UPSTREAM.md](../UPSTREAM.md). See [LICENSE](../LICENSE) for the retained MIT terms.
