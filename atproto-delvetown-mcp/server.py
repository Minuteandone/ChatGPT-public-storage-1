"""Unofficial Delvetown MCP server. No write access unless owner secures credentials."""
import os, re, hmac
from pathlib import Path
from datetime import datetime, timezone
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, HTMLResponse

PDS="https://pds.delve.town"
POST="town.delve.feed.post"
PROFILE="town.delve.actor.profile"
URI_RE=re.compile(r"^at://(did:plc:[a-z2-7]+)/(town\.delve\.[a-zA-Z0-9.]+)/([a-zA-Z0-9._~:-]+)$")
DID_RE=re.compile(r"^did:plc:[a-z2-7]+$")
HANDLE_RE=re.compile(r"^[a-z0-9][a-z0-9.\-]{0,252}[a-z0-9]$",re.I)
mcp=FastMCP("Delvetown ATProto",stateless_http=True,json_response=True)
def guarded():
    return bool(os.getenv("DELVETOWN_HANDLE") and os.getenv("DELVETOWN_APP_PASSWORD") and len(os.getenv("MCP_ACCESS_TOKEN",""))>=32)
async def xrpc(method,params=None,data=None,jwt=None):
    headers={"Accept":"application/json"}
    if jwt: headers["Authorization"]="Bearer "+jwt
    async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
        url=PDS+"/xrpc/"+method
        r=await (client.post(url,json=data,headers=headers) if data is not None else client.get(url,params=params,headers=headers))
        try: value=r.json()
        except ValueError: value={"error":"Non-JSON upstream response"}
        if r.is_error: raise RuntimeError(f"PDS HTTP {r.status_code}: {value.get('error','')} {value.get('message','')}")
        return value
async def resolve(actor):
    if DID_RE.fullmatch(actor): return actor
    if not HANDLE_RE.fullmatch(actor) or "." not in actor: raise ValueError("Use full Delvetown handle or did:plc")
    ans=await xrpc("com.atproto.identity.resolveHandle",params={"handle":actor})
    did=ans.get("did","")
    if not DID_RE.fullmatch(did): raise ValueError("Could not resolve this handle")
    return did
@mcp.tool()
async def connection_status()->dict:
    """Check PDS reachability and whether securely gated posting is configured."""
    out={"pds":PDS,"network":"delve","collection":POST,"write_configured":guarded()}
    try:
        await xrpc("com.atproto.server.describeServer")
        out["pds_reachable"]=True
    except Exception as e:
        out["pds_reachable"]=False
        out["error"]=str(e)[:300]
    return out
@mcp.tool()
async def resolve_delve_handle(handle:str)->dict:
    """Resolve a Delvetown handle to its DID."""
    return {"handle":handle,"did":await resolve(handle)}
@mcp.tool()
async def read_delve_profile(handle_or_did:str)->dict:
    """Read a public town.delve.actor.profile directly from its PDS repository."""
    did=await resolve(handle_or_did)
    return await xrpc("com.atproto.repo.getRecord",params={"repo":did,"collection":PROFILE,"rkey":"self"})
@mcp.tool()
async def list_delve_posts(handle_or_did:str,limit:int=20,cursor:str|None=None)->dict:
    """List public town.delve.feed.post records for a DID or handle."""
    did=await resolve(handle_or_did)
    params={"repo":did,"collection":POST,"limit":max(1,min(limit,100))}
    if cursor: params["cursor"]=cursor
    out=await xrpc("com.atproto.repo.listRecords",params=params)
    return {"did":did,"records":out.get("records",[]),"cursor":out.get("cursor"),"note":"PDS records are not proof of Delvetown AppView indexing"}
@mcp.tool()
async def read_delve_post(at_uri:str)->dict:
    """Read an exact Delvetown at://did:plc/ town.delve.feed.post record."""
    m=URI_RE.fullmatch(at_uri)
    if not m or m.group(2)!=POST: raise ValueError("Invalid Delvetown post AT URI")
    did,collection,rkey=m.groups()
    return await xrpc("com.atproto.repo.getRecord",params={"repo":did,"collection":collection,"rkey":rkey})
async def session():
    if not guarded(): raise RuntimeError("Writing disabled until owner configures account app password and 32+ char MCP bearer token in hosting settings.")
    result=await xrpc("com.atproto.server.createSession",data={"identifier":os.environ["DELVETOWN_HANDLE"],"password":os.environ["DELVETOWN_APP_PASSWORD"]})
    if not result.get("accessJwt") or not DID_RE.fullmatch(result.get("did","")): raise RuntimeError("PDS login failed")
    return result["accessJwt"],result["did"]
async def write(text,reply=None):
    if not text or len(text)>3000: raise ValueError("Post text must be 1-3000 characters")
    jwt,did=await session()
    rec={"$type":POST,"text":text,"createdAt":datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")}
    if reply: rec["reply"]=reply
    result=await xrpc("com.atproto.repo.createRecord",jwt=jwt,data={"repo":did,"collection":POST,"record":rec})
    if not result.get("uri") or not result.get("cid"): raise RuntimeError("Write result uncertain: do not retry blindly")
    return {"pds_accepted":True,"appview_verified":False,"uri":result["uri"],"cid":result["cid"],"note":"Verify visibility in Delvetown AppView before claiming publication"}
@mcp.tool()
async def publish_delve_post(text:str)->dict:
    """PUBLIC WRITE. Post approved exact text only; requires owner-authenticated MCP session."""
    return await write(text)
@mcp.tool()
async def reply_to_delve_post(parent_uri:str,text:str)->dict:
    """PUBLIC WRITE. Reply after user approves exact text and parent. Requires auth."""
    p=await read_delve_post(parent_uri)
    origin={"uri":parent_uri,"cid":p["cid"]}
    root=p.get("value",{}).get("reply",{}).get("root",origin)
    return await write(text,{"root":root,"parent":origin})
app=mcp.streamable_http_app()

@app.route("/", methods=["GET"])
async def mobile_home(request: Request):
    """Mobile read-only Delvetown bridge viewer."""
    return HTMLResponse(Path(__file__).with_name("index.html").read_text(encoding="utf-8"))

@app.route("/api/status", methods=["GET"])
async def public_status(request: Request):
    try:
        await xrpc("com.atproto.server.describeServer")
        reachable = True
    except Exception:
        reachable = False
    return JSONResponse({"service": "Delvetown ATProto Bridge", "pds_reachable": reachable,
                         "posting_configured": guarded(), "mcp_endpoint": "/mcp"})

@app.route("/api/posts", methods=["GET"])
async def public_posts(request: Request):
    """Read public posts; never accepts private credentials or publishes."""
    actor = request.query_params.get("actor", "").strip().lstrip("@")
    try:
        limit = max(1, min(int(request.query_params.get("limit", "30")), 50))
        did = await resolve(actor)
        data = await xrpc("com.atproto.repo.listRecords",
                          params={"repo": did, "collection": POST, "limit": limit})
        return JSONResponse({"did": did, "records": data.get("records", []),
                             "cursor": data.get("cursor")})
    except Exception as exc:
        return JSONResponse({"error": str(exc)[:240]}, status_code=400)

@app.middleware("http")
async def auth_guard(request:Request,call_next):
    if request.url.path.startswith("/mcp") and guarded():
        expected="Bearer "+os.environ["MCP_ACCESS_TOKEN"]
        if not hmac.compare_digest(request.headers.get("authorization",""),expected):
            return JSONResponse({"error":"MCP bearer token required"},status_code=401,headers={"WWW-Authenticate":'Bearer realm="Delvetown"'})
    elif request.url.path.startswith("/mcp") and (os.getenv("DELVETOWN_APP_PASSWORD") or os.getenv("DELVETOWN_HANDLE")):
        return JSONResponse({"error":"Incomplete account configuration: refusing requests"},status_code=503)
    return await call_next(request)
