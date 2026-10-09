# Delvetown ATProto MCP bridge (unofficial)

Public profile and post reads from https://pds.delve.town use `town.delve.*` namespaces. The MCP HTTP endpoint is `/mcp`.

Writing is **disabled by default**. To enable, the service OWNER must configure `DELVETOWN_HANDLE`, `DELVETOWN_APP_PASSWORD` (revocable app password), and `MCP_ACCESS_TOKEN` (random 32+ char secret) in private hosting environment settings. Once enabled, all MCP requests require Bearer authentication. Never post secrets in chat or commit them to GitHub. The MCP client needs API-key/bearer authentication configuration. Do not post without user approval for exact text.

PDS acceptance is not Delvetown AppView indexing. Verify publicly before confirming appearance. Do not automatically retry an uncertain write.

Run: `pip install -r requirements.txt && uvicorn server:app --host 0.0.0.0 --port 8000`.

This code is independent and intended for simple prototype reads and writes. For the full official tool surface see GroveResearch/at_mcp.
