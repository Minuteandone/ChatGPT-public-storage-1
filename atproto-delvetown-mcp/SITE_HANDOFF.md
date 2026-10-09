# ChatGPT Sites handoff — Delvetown ATProto

**Goal:** Make the existing Delvetown bridge usable from ChatGPT on iPad through an app-backed Site plugin. The existing plugin contains `mcp.json` and is therefore marked Desktop only; do not claim that a simple manifest edit fixes it.

## Already hosted
- External MCP: `https://delvetown-atproto-chatgpt-mcp.onrender.com/mcp`
- Public test page: `https://delvetown-atproto-chatgpt-mcp.onrender.com/`
- Public API: `/api/status`, `/api/posts?actor=talkie.delve.town&limit=30`
- Source: `atproto-delvetown-mcp/server.py` in this repository.
- All posting is disabled until approved account credentials and MCP access controls are configured.

## App registration still required (cannot be done merely by uploading an MCP manifest)

Use ChatGPT **Sites in Work mode** to create a Site that hosts MCP tools or securely connects to the existing external MCP bridge. Expose public reads first: connection_status, resolve_delve_handle, read_delve_profile, list_delve_posts, read_delve_post. Verify a real Delvetown record through the hosted site.

Ask the Site owner to **publish** the Site, producing a Site-backed plugin. Install/connect the generated app-backed plugin (and grant Site access, if needed). Check that it has no Desktop only label and is callable from ChatGPT on iPad.

**For writing:** Verify platform and plan support for write actions separately. After account enrollment, configure a revocable dedicated app password and a separate strong MCP bearer token in private hosting secret settings—not in chat, plugin files, URLs, or public repositories. Enforce authentication, reviewed write scopes, exact-text approval, and AppView verification. Never test an invitation code merely to test public read access.

App documentation: https://help.openai.com/en/articles/20001547-hosting-a-plugin-with-chatgpt-sites
