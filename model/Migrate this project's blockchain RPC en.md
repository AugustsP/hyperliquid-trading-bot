Migrate this project's blockchain RPC endpoints to Dwellir. Follow the phases below in order. Use subagents and background processes to parallelize work wherever your tooling supports it.

## Phase 1 — Environment & Endpoint Discovery

1. Check whether the Dwellir CLI is installed by running `dwellir --version`. If the command is not found, suggest the user install it:
   curl -fsSL https://raw.githubusercontent.com/dwellir-public/cli/main/scripts/install.sh | sh
2. Obtain the full list of Dwellir-supported chains, networks, and node types (full vs archive). Try one of these approaches in order until one succeeds:
   a. **CLI** (preferred): Run `dwellir endpoints list` to get the complete endpoint catalog.
   b. **Documentation**: If the CLI is unavailable or the user declines to install it, fetch https://www.dwellir.com/docs.md or https://www.dwellir.com/networks.md for the supported endpoint list.
   c. **Dashboard export**: As a last resort, ask the user to go to dashboard.dwellir.com/endpoints and press the Export button (top-left) to export all endpoints as CSV, Markdown, or JSON, then share the file with you.
3. Check whether the project uses separate configurations per environment (production, staging, development, etc.). If it does, ask the user to provide a Dwellir API key for each environment. If there is only one environment, ask for a single key.

## Phase 2 — Codebase Discovery

Scan the entire codebase in parallel where possible:

1. Find every RPC endpoint URL (look for domains like infura.io, alchemy.com, quicknode.com, chainstack.com, ankr.com, blast.io, drpc.org, and any other known RPC providers, as well as raw IP/port patterns and chain-specific gateway URLs).
2. Identify each endpoint's chain, network, and authentication method (API key in URL path, header, query param, or none).
3. Determine whether the code requires an archive node or a full node for each endpoint (look for calls to historical state such as eth_getBalance at old block heights, debug_*/trace_* namespaces, or large block-range log filters).
4. Check if the codebase interacts with Hyperliquid. If it does, suggest that the user install Dwellir's Hyperliquid Skills: `npx skills add https://github.com/dwellir-public/hyperliquid-skills`

## Phase 3 — Compatibility Matching

For each discovered endpoint:

1. Compare the chain + network against the Dwellir endpoints list from Phase 1. Note that some providers (especially for EVM chains) use chain ID-based naming in their URLs rather than chain + network names — resolve any ambiguity by calling the endpoint's RPC method for chain ID (e.g., `eth_chainId`) and comparing the result against the chain ID returned by the corresponding Dwellir endpoint to confirm they serve the same network.
2. If the code requires an archive node and Dwellir only offers a full node for that chain, mark the endpoint as unsupported and do NOT migrate it.
3. For EVM chains, check whether the codebase depends on client-specific response shapes (e.g., Geth/Erigon trace formats vs Reth, differences in debug_traceTransaction output, or Parity-style trace_* responses). Use web search if needed to understand current client-level differences. Flag any potential incompatibilities.

## Phase 4 — Migration

1. Create a new branch (e.g., `chore/migrate-to-dwellir`) — NEVER commit directly to main.
2. For each supported endpoint, replace the provider URL with the equivalent Dwellir endpoint URL and update the authentication to use the correct Dwellir API key for each environment. Preserve the existing configuration pattern (env var, config file, etc.).
3. If any endpoints, chains, or networks in the codebase are NOT supported by Dwellir, do not touch them.

## Phase 5 — Summary

Present a clear summary with:

- ✅ **Migrated**: list of endpoints successfully switched to Dwellir (chain, network, full/archive).
- ⚠️ **Flagged**: any EVM client compatibility concerns the user should verify.
- ❌ **Not supported**: list of endpoints/chains/networks Dwellir does not currently support, along with whether each requires a full or archive node and the estimated monthly request volume if determinable from the code. Ask the user to reach out to support@dwellir.com or the team on https://t.me/dwellir with this list so Dwellir can evaluate adding support.

If there are any questions about supported RPC methods or Dwellir services, consult https://www.dwellir.com/docs/llms.txt and https://www.dwellir.com/docs.md for authoritative reference.

Commit the changes and ask the user whether you should push the branch to origin and open a pull request.