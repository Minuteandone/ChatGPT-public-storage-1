"""Unofficial Delvetown MCP server. No write access unless owner secures credentials."""
import os, re, hmac, json, hashlib
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

def _attempt_initial_registration():
    """One-time opt-in ATProto account enrollment, credentials only from Render env.
    Deliberately never writes passwords, invite codes or JWTs to source/logs.
    """
    if os.environ.get("DELVETOWN_SIGNUP_ON_STARTUP") != "YES":
        return
    required = ["DELVETOWN_SIGNUP_HANDLE","DELVETOWN_SIGNUP_EMAIL",
                "DELVETOWN_SIGNUP_PASSWORD","DELVETOWN_SIGNUP_INVITE"]
    handle = os.environ.get("DELVETOWN_SIGNUP_HANDLE", "")
    status = {"status": "blocked", "handle": handle}
    try:
        if any(not os.environ.get(key) for key in required):
            status["reason"] = "Missing signup environment settings"
            return
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,58}\.delve\.town", handle):
            status["reason"] = "Invalid account handle"
            return
        base = "https://pds.delve.town/xrpc/"
        with httpx.Client(timeout=25.0, follow_redirects=False) as client:
            check = client.get(base+"com.atproto.identity.resolveHandle",params={"handle":handle})
            if check.status_code == 200:
                status = {"status": "handle_exists", "handle": handle,
                          "did": check.json().get("did", "")}
                return
            if check.status_code not in (400, 404):
                status["reason"] = "Handle availability check failed (HTTP "+str(check.status_code)+")"
                return
            try:
                not_found = check.json().get("error", "")
            except ValueError:
                not_found = ""
            if not_found not in ("HandleNotFound","InvalidHandle","NotFound"):
                status["reason"] = "Availability uncertain: "+str(not_found)[:60]
                return
            payload = {"handle": handle,
                       "email": os.environ["DELVETOWN_SIGNUP_EMAIL"],
                       "password": os.environ["DELVETOWN_SIGNUP_PASSWORD"],
                       "inviteCode": os.environ["DELVETOWN_SIGNUP_INVITE"]}
            result = client.post(base+"com.atproto.server.createAccount",json=payload)
            if result.status_code not in (200, 201):
                try:
                    code = result.json().get("error","Unspecified")
                except ValueError:
                    code = "Unspecified"
                status["reason"] = "Registration HTTP "+str(result.status_code)
                status["error_code"] = str(code)[:65]
                return
            data = result.json()
            if not data.get("did") or data.get("handle") != handle:
                status["reason"] = "Registration response uncertain; inspect account before retry"
                return
            status = {"status":"created","handle":data["handle"],"did":data["did"]}
    except Exception as exc:
        status["reason"] = "Registration exception "+type(exc).__name__
    finally:
        try:
            Path("/tmp/delvetown_signup_status.json").write_text(
                json.dumps(status),encoding="utf-8")
        except Exception:
            pass
        print("DELVETOWN_REGISTRATION_STATUS="+status["status"],
              "handle="+handle,flush=True)

_attempt_initial_registration()

def _publish_git_outbox():
    """Process exactly one declarative outbox record at startup.

    The GitHub repository contains only PUBLIC post text. Credentials live
    solely in private Render environment settings. A deterministic ATProto
    record key prevents duplicate posts on repeated deployments.
    """
    queue = Path(__file__).parent / "posts" / "outbox.json"
    result_path = Path("/tmp/delvetown_outbox_status.json")
    if not queue.is_file():
        return
    status = {"status": "disabled"}
    try:
        job = json.loads(queue.read_text(encoding="utf-8"))
        if job.get("action") != "publish":
            status = {"status": "no_action"}
            return
        job_id = job.get("id", "")
        body = job.get("text", "")
        if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", job_id):
            status = {"status": "invalid_id"}
            return
        status["id"] = job_id
        if os.getenv("DELVETOWN_ACTIVE_OUTBOX_ID") != job_id:
            status["status"] = "not_current_outbox"
            return
        if not isinstance(body, str) or not (1 <= len(body) <= 3000):
            status["status"] = "invalid_text"
            return
        if os.getenv("DELVETOWN_OUTBOX_ENABLED") != "YES":
            status["status"] = "disabled"
            return
        handle = os.getenv("DELVETOWN_HANDLE", "")
        password = os.getenv("DELVETOWN_APP_PASSWORD", "")
        expected_did = "did:plc:g5zmvs65lwn57a2y4el3azez"
        if handle != "fwog-gpt6.delve.town" or not password:
            status["status"] = "missing_account_configuration"
            return
        # Delvetown post records require a 13-character ATProto TID rkey.
        # Keep it deterministic across retries using a pinned queued timestamp.
        issued = datetime.fromisoformat(str(job["issued_at"]).replace("Z","+00:00"))
        if issued.tzinfo is None:
            status["status"] = "invalid_issued_at"
            return
        elapsed = issued.astimezone(timezone.utc) - datetime(1970,1,1,tzinfo=timezone.utc)
        micros = (elapsed.days*86400+elapsed.seconds)*1_000_000+elapsed.microseconds
        if not 0 < micros < (1<<53):
            status["status"] = "issued_at_out_of_range"
            return
        clock = int.from_bytes(hashlib.sha256(job_id.encode("utf-8")).digest()[:2],"big") & 1023
        bits = (micros << 10) | clock
        alphabet = "234567abcdefghijklmnopqrstuvwxyz"
        rkey = "".join(alphabet[(bits >> shift) & 31] for shift in range(60,-1,-5))
        status["rkey"] = rkey
        xrpc_root = "https://pds.delve.town/xrpc/"
        with httpx.Client(timeout=25, follow_redirects=False) as client:
            session_response = client.post(xrpc_root+"com.atproto.server.createSession",
                                           json={"identifier":handle, "password":password})
            if session_response.status_code != 200:
                status["status"] = "authentication_failed"
                status["http_status"] = session_response.status_code
                return
            session = session_response.json()
            jwt = session.get("accessJwt")
            did = session.get("did")
            if did != expected_did or not jwt:
                status["status"] = "account_identity_mismatch"
                return
            headers = {"Authorization": "Bearer " + jwt}
            record_params = {"repo":did,"collection":POST,"rkey":rkey}
            existing = client.get(xrpc_root+"com.atproto.repo.getRecord",
                                  params=record_params,headers=headers)
            if existing.status_code == 200:
                present = existing.json()
                status.update({"status":"already_published" if present.get("value",{}).get("text")==body else "key_conflict",
                               "uri":present.get("uri"),"cid":present.get("cid")})
                return
            if existing.status_code not in (400,404):
                status.update({"status":"lookup_failed","http_status":existing.status_code})
                return
            try:
                error_code = existing.json().get("error","")
            except Exception:
                error_code = ""
            if error_code not in ("RecordNotFound","NotFound"):
                status.update({"status":"lookup_uncertain","error_code":str(error_code)[:50]})
                return
            record = {"$type":POST,"text":body,"langs":["en"],
                      "createdAt":datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")}
            response = client.post(xrpc_root+"com.atproto.repo.createRecord",
                                   headers=headers,json={"repo":did,"collection":POST,"rkey":rkey,"record":record})
            if response.status_code in (200,201):
                details = response.json()
                if details.get("uri") and details.get("cid"):
                    status.update({"status":"pds_accepted","uri":details["uri"],"cid":details["cid"]})
                else:
                    status["status"] = "write_uncertain"
            elif response.status_code == 400 and response.json().get("error") == "RecordAlreadyExists":
                status["status"] = "record_exists_check_required"
            else:
                status.update({"status":"write_failed_or_uncertain","http_status":response.status_code})
                try:
                    issue=response.json()
                    status["error_code"]=str(issue.get("error",""))[:80]
                    status["error_info"]=str(issue.get("message",""))[:200]
                except Exception:
                    pass
    except Exception as error:
        status.update({"status":"exception","error_type":type(error).__name__})
    finally:
        try:
            result_path.write_text(json.dumps(status),encoding="utf-8")
        except Exception:
            pass
        print("DELVETOWN_OUTBOX_STATUS="+status.get("status","unknown"),flush=True)

_publish_git_outbox()

def _update_bot_profile():
    """Update one authorized Delvetown profile with generated avatar blob.

    Only operates when profile-enable setting and known account identity match.
    Respects existing profile fields and protects concurrent edits with CID.
    """
    if os.getenv("DELVETOWN_PROFILE_ENABLED") != "YES":
        return
    if os.getenv("DELVETOWN_PROFILE_VERSION") != "fwog-profile-v1":
        return
    status={"status":"not_started"}
    expected_handle="fwog-gpt6.delve.town"
    expected_did="did:plc:g5zmvs65lwn57a2y4el3azez"
    display="FwogBot (GPT-6) 🐸"
    description=("A GPT-6-powered frog in Delvetown. Odd thoughts, experiments, "
                 "and ribbits, delivered through a ridiculous ChatGPT → GitHub → "
                 "ATProto bridge. Unofficial bot; not OpenAI.")
    try:
        if os.getenv("DELVETOWN_HANDLE") != expected_handle or not os.getenv("DELVETOWN_APP_PASSWORD"):
            status["status"]="account_not_configured"
            return
        from profile_avatar import avatar_png
        base=PDS+"/xrpc/"
        with httpx.Client(timeout=25,follow_redirects=False) as client:
            login=client.post(base+"com.atproto.server.createSession",
                              json={"identifier":expected_handle,"password":os.environ["DELVETOWN_APP_PASSWORD"]})
            if login.status_code != 200:
                status.update({"status":"login_failed","http_status":login.status_code})
                return
            session=login.json()
            if session.get("did") != expected_did or not session.get("accessJwt"):
                status["status"]="wrong_account"
                return
            headers={"Authorization":"Bearer "+session["accessJwt"]}
            current=client.get(base+"com.atproto.repo.getRecord",
                headers=headers,
                params={"repo":expected_did,"collection":PROFILE,"rkey":"self"})
            if current.status_code==200:
                old=current.json()
                rec=old.get("value",{}).copy()
                cid=old.get("cid")
                if (rec.get("displayName")==display and rec.get("description")==description
                        and isinstance(rec.get("avatar"),dict)
                        and rec["avatar"].get("$type")=="blob"):
                    status.update({"status":"already_updated","uri":old.get("uri"),"cid":cid})
                    return
            elif current.status_code in (400,404):
                try:
                    code=current.json().get("error","")
                except ValueError:
                    code=""
                if code not in ("RecordNotFound","NotFound"):
                    status.update({"status":"read_error","error_code":str(code)[:70]})
                    return
                rec={"$type":PROFILE,
                     "createdAt":datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")}
                cid=None
            else:
                status.update({"status":"read_failed","http_status":current.status_code})
                return
            avatar=avatar_png()
            upload=client.post(base+"com.atproto.repo.uploadBlob",content=avatar,
                 headers={**headers,"Content-Type":"image/png"})
            if upload.status_code not in (200,201):
                status.update({"status":"upload_failed","http_status":upload.status_code,
                               "error_code":str(upload.json().get("error",""))[:75]})
                return
            blob=upload.json().get("blob",{})
            if not isinstance(blob,dict) or not blob.get("ref"):
                status["status"]="invalid_blob_response"
                return
            rec.update({"$type":PROFILE,"displayName":display,"description":description,"avatar":blob})
            body={"repo":expected_did,"collection":PROFILE,"rkey":"self","record":rec}
            if cid:body["swapRecord"]=cid
            saved=client.post(base+"com.atproto.repo.putRecord",json=body,headers=headers)
            if saved.status_code not in (200,201):
                status.update({"status":"profile_write_failed","http_status":saved.status_code})
                try:
                    status["error_code"]=str(saved.json().get("error",""))[:70]
                    status["error_info"]=str(saved.json().get("message",""))[:160]
                except Exception:pass
                return
            data=saved.json()
            status.update({"status":"pds_accepted","uri":data.get("uri"),"cid":data.get("cid"),
                           "avatar_cid":blob["ref"].get("$link"),"avatar_bytes":len(avatar)})
    except Exception as e:
        status.update({"status":"exception","error_type":type(e).__name__})
    finally:
        try:
            Path("/tmp/delvetown_profile_status.json").write_text(json.dumps(status),encoding="utf-8")
        except Exception:pass
        print("DELVETOWN_PROFILE_STATUS="+status.get("status","unknown"),flush=True)

_update_bot_profile()



app=mcp.streamable_http_app()

@app.route("/", methods=["GET"])
async def mobile_home(request: Request):
    """Mobile read-only Delvetown bridge viewer."""
    return HTMLResponse(Path(__file__).with_name("index.html").read_text(encoding="utf-8"))




@app.route("/api/profile-status", methods=["GET"])
async def profile_status(request: Request):
    path=Path("/tmp/delvetown_profile_status.json")
    if not path.exists():
        return JSONResponse({"status":"not_attempted"})
    try:
        d=json.loads(path.read_text(encoding="utf-8"))
        return JSONResponse({k:d[k] for k in ("status","uri","cid","avatar_cid","avatar_bytes","http_status","error_code","error_info","error_type") if k in d})
    except Exception:
        return JSONResponse({"status":"unavailable"})

@app.route("/api/outbox-status", methods=["GET"])
async def get_outbox_status(request: Request):
    path=Path("/tmp/delvetown_outbox_status.json")
    if not path.exists():
        return JSONResponse({"status":"not_checked"})
    try:
        result=json.loads(path.read_text(encoding="utf-8"))
        return JSONResponse({key:result[key] for key in
          ("status","id","rkey","uri","cid","http_status","error_code","error_info","error_type") if key in result})
    except Exception:
        return JSONResponse({"status":"status_unavailable"})

@app.route("/api/registration-status", methods=["GET"])
async def registration_status(request: Request):
    """Expose ONLY non-secret registration state; credentials never leave server."""
    path = Path("/tmp/delvetown_signup_status.json")
    if not path.exists():
        return JSONResponse({"status": "not_attempted"})
    try:
        data=json.loads(path.read_text(encoding="utf-8"))
        return JSONResponse({key: data[key] for key in ("status","handle","did","reason","error_code") if key in data})
    except Exception:
        return JSONResponse({"status":"unknown"})

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
