<h1 align="center">
  <img src="https://github.com/user-attachments/assets/0cc687fb-89c4-43fa-a056-d89c307215ad" alt="Kuest" height="96" /><br/>
  Python SDK
</h1>

This is the public Kuest source repository for the white-label unified Python SDK. The
package and imports remain neutral so operator distributions can carry their own identity.

The SDK combines market discovery, CLOB data and orders, and Deposit Wallet relayer
workflows on Polygon. It adapts the [upstream unified SDK](https://github.com/Polymarket/py-sdk)
for Kuest's deployed contracts and APIs. Live trading has not been verified.

## Supported scope

- Polygon mainnet (chain ID 137), Circle USDC, Conditional Tokens, and the configured CTF and Neg Risk exchanges.
- Orders use EIP-712 `CTF Exchange` version `2`, a verified Deposit Wallet as maker and signer, signature type `3`, and a CLOB API key as the order owner.
- Relayer submissions use builder credentials and `WALLET` or `WALLET-CREATE` payloads. Nonce and transaction reads use `/nonce` and `/transaction`.
- Standard and NegRisk CTF split, merge, and redeem use the deployed Conditional Tokens and NegRiskAdapter contracts. NegRisk redeem uses the adapter's YES/NO amount ABI. These calls require the caller's relevant USDC allowance or CTF operator approval; trading approvals for the exchanges do not grant those permissions.
- RFQ is intentionally disabled for this product, including the ordinary RFQ supported by the CLOB backend. Specialized session-key management and upstream protocol V2 Router position operations reject locally.
- Position-backed V3 orders, combo RFQ, collateral return, and Safe/Proxy relayer submissions fail locally. Perps, realtime, sports, bridge, and other upstream-only services are not configured.
- Builder-attributed trade listing fails locally because the current CLOB ignores `builder_code`; see [COMPATIBILITY.md](./COMPATIBILITY.md).
- All network endpoints default to `unconfigured.invalid`. An integrator must supply approved HTTPS/WSS service URLs and a Polygon RPC URL explicitly.

For a direct GitHub checkout, supply endpoint configuration explicitly. An operator ZIP
may include `.sdk/site-config.json` with the existing `site_url`, `builder_mode`,
`geoblock`, `builder_code`, and `order_metadata` fields. That file supplies operator
attribution and site checks without changing the public package name. It must contain
no private keys. A nonempty configured builder code takes precedence over a per-order
builder code, including the zero bytes32 value, which means no attribution.
`builder_mode=true` requires a nonzero code. Market discovery uses the configured site's active event list.

The source distribution is named `kuest-sdk`; Python imports remain `market_sdk`.
The distribution is published as [`kuest-sdk`](https://pypi.org/project/kuest-sdk/). Install it with `pip install kuest-sdk` and import it as `market_sdk`.

## Read-only example

```python
import os
from market_sdk import PublicClient, configured_environment

environment = configured_environment(
    clob_url=os.environ["SDK_CLOB_URL"],
    clob_ws_url=os.environ["SDK_CLOB_WS_URL"],
    relayer_url=os.environ["SDK_RELAYER_URL"],
    gamma_url=os.environ["SDK_GAMMA_URL"],
    data_url=os.environ["SDK_DATA_URL"],
    rpc_url=os.environ["SDK_RPC_URL"],
)

with PublicClient(environment=environment) as client:
    book = client.get_order_book(token_id=os.environ["SDK_TOKEN_ID"])
    print(book)
```

Wallet deployment requires separate builder credentials. No live order or transaction tests have been run.

## Origin and license

Imported from [Polymarket/py-sdk](https://github.com/Polymarket/py-sdk) at commit [`860ac384931ea55ed08a92219c9d27c02f6966cf`](https://github.com/Polymarket/py-sdk/commit/860ac384931ea55ed08a92219c9d27c02f6966cf). See [UPSTREAM.md](./UPSTREAM.md). Original copyright and MIT terms remain in [LICENSE](./LICENSE).

Kuest Engineering adapted the upstream code for the verified service API,
contracts, and operator packaging.
