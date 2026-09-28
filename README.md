# CMN-C2-710 — Enterprise High-Performance Vector Search & Knowledge Retrieval Q&A

> **Category**: Cat 2 (orchestrates multiple steps to accomplish a specific use case)
> **Industry**: CMN

## Overview

Answers architecture and tuning questions about vector search: index configuration, choice of
approximate-nearest-neighbour algorithm, latency tuning, hybrid (dense + BM25) search, Japan
on-premise deployment under APPI, and reading benchmark results. The input is the question as
text; optional `constraints` (scale, latency target, deployment) are read from
`input_context`. Questions that contain a credential, a database connection string or a URL
with a port are rejected.

The question is classified into one of the six domains by keyword. The agent then ranks the
passages of a small built-in knowledge base for that domain by word overlap with the question
(a placeholder for real dense + BM25 retrieval), attaches links to public reference
documentation for the domain, and combines the constraints into a context block.

With a language model client configured, the model writes a recommendation grounded in those
passages. The HTTP entry point wires an Anthropic client only when an `ANTHROPIC_API_KEY` secret
is available. Without a model the agent returns a retrieval-only answer that lists the matching
passages and references and says that no model was used. An output check fails the run if the
answer contains benchmark figures (latency, QPS, percentages) that do not appear in the
retrieved passages, and appends a note to consult a data-protection officer whenever the
answer mentions on-premise or APPI compliance.

This is an agent template built with the **AGENTIC STAR** development platform and the
**AgentCore Framework**. It is intended to be taken as a starting point: fork it, adapt it to
your own data and policies, and run it inside your own AGENTIC STAR deployment.

## Requirements

**This template does not run standalone.** It requires:

| Requirement | Notes |
|---|---|
| **AGENTIC STAR platform** | The agent connects to the platform at start-up. Without it, start-up fails immediately (see *Behaviour without the platform* below). Deployment guides and API documentation: [AGENTIC STAR Developers](https://developers.fd.agenticstar.tm.softbank.jp/) |
| **AgentCore Framework** (`agenticstar-agentcore`) | Installed from PyPI as a dependency. |
| Python | 3.11 or later |

```bash
pip install -e .
```

### Behaviour without the platform

The framework is designed to run **only** on AGENTIC STAR. There is no fallback or degraded
mode. If the platform is unreachable or the SDK version does not match, the agent raises
`PlatformRequired` during graph compile / start-up preflight rather than starting in a partially
working state. This is intentional — a half-running agent is worse than one that refuses to start.

## Quick Start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest tests/ -v
```

Tests run without a platform connection. Running the agent itself does not.

## Project Structure

```
src/          agent implementation (nodes, services, schemas)
tests/        unit, integration and boundary tests
config/       agent configuration
docs/         design and test specification
```

See `docs/02_design.md` for the design and `docs/03_test_spec.md` for the test specification.

## Customising

1. Adjust `config/` for your own environment and policies.
2. Replace the knowledge sources and sample data with your own.
3. Review the node implementations under `src/nodes/` for domain-specific logic.
4. Re-run the test suite.

## License

MIT — see [LICENSE](LICENSE).

## Status of this repository

This template is published **as is**, by its individual author, under the MIT license. It carries
**no warranty and no support commitment**, and no organisation stands behind its behaviour or
fitness for any purpose. Issues and pull requests may or may not receive a response; that is at
the sole discretion of the repository owner.
