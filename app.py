from __future__ import annotations

import hashlib
import hmac
import os
import threading
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, redirect, render_template_string, request, session, url_for

app = Flask(__name__)

SYNC_TOKEN = os.environ.get("SYNC_TOKEN", "").strip()
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "").strip()
_secret_material = os.environ.get("DASHBOARD_SECRET_KEY", "").strip() or f"{SYNC_TOKEN}|{DASHBOARD_PASSWORD}|paleologos-production"
app.secret_key = hashlib.sha256(_secret_material.encode("utf-8")).hexdigest()
app.config.update(
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)

_snapshot_lock = threading.Lock()
_latest_snapshot = None
_received_at = None

LOGIN_HTML = r'''<!doctype html><html lang="el"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0f172a"><title>Paleologos Production</title><style>*{box-sizing:border-box}body{margin:0;background:#08111f;color:#f8fafc;font-family:system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh;display:grid;place-items:center;padding:20px}.box{width:min(430px,100%);background:#111827;border:1px solid #26344d;border-radius:20px;padding:24px;box-shadow:0 24px 70px #0006}h1{margin:0 0 5px;font-size:24px}p{color:#94a3b8;margin:0 0 20px}input,button{width:100%;min-height:50px;border-radius:12px;font-size:16px}input{background:#0f172a;color:#fff;border:1px solid #334155;padding:12px 14px;margin-bottom:10px}button{border:0;background:#0ea5e9;color:white;font-weight:800}.err{background:#450a0a;color:#fecaca;border:1px solid #7f1d1d;padding:10px 12px;border-radius:10px;margin-bottom:12px}.small{font-size:12px;color:#64748b;margin-top:14px}</style></head><body><form class="box" method="post"><h1>Paleologos Production</h1><p>Απομακρυσμένη προβολή παραγωγής</p>{% if setup %}<div class="err">Δεν έχει οριστεί DASHBOARD_PASSWORD στο Railway.</div>{% elif error %}<div class="err">Λάθος κωδικός.</div>{% endif %}<input name="password" type="password" placeholder="Κωδικός πρόσβασης" autocomplete="current-password" {% if setup %}disabled{% endif %}><button type="submit" {% if setup %}disabled{% endif %}>Σύνδεση</button><div class="small">Read-only dashboard</div></form></body></html>'''

DASHBOARD_HTML = r'''<!doctype html>
<html lang="el"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0f172a"><meta name="mobile-web-app-capable" content="yes">
<link rel="manifest" href="/static/manifest.json"><link rel="icon" href="/static/icon-192.png?v=191"><link rel="apple-touch-icon" href="/static/icon-192.png?v=191"><title>Paleologos Production</title>
<style>
:root{--bg:#09111f;--panel:#111827;--line:#26344d;--muted:#94a3b8;--text:#f8fafc;--blue:#0ea5e9;--green:#22c55e;--amber:#f59e0b;--red:#ef4444}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#08111f,#0b1220);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}.wrap{max-width:1180px;margin:auto;padding:16px}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:14px}.top h1{font-size:22px;margin:0}.sub{color:var(--muted);font-size:13px;margin-top:3px}.right{display:flex;align-items:center;gap:8px}.badge{background:#172554;color:#bfdbfe;border-radius:999px;padding:7px 10px;font-size:11px;font-weight:800}.logout{color:#cbd5e1;text-decoration:none;font-size:12px}.sync{background:#111827;border:1px solid var(--line);border-radius:13px;padding:11px 13px;margin-bottom:14px;color:#cbd5e1;font-size:13px}.sync.ok strong{color:#86efac}.sync.stale strong{color:#fde68a}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.card{background:rgba(17,24,39,.94);border:1px solid var(--line);border-radius:16px;padding:15px}.label{font-size:12px;color:var(--muted)}.value{font-size:29px;font-weight:850;margin-top:5px}.green{color:#86efac}.amber{color:#fcd34d}.red{color:#fca5a5}.progress{margin:12px 0 18px;background:#172033;border:1px solid var(--line);border-radius:14px;padding:14px}.progresshead{display:flex;justify-content:space-between;color:#cbd5e1;font-size:13px}.bar{height:9px;background:#334155;border-radius:99px;overflow:hidden;margin-top:9px}.bar span{display:block;height:100%;background:linear-gradient(90deg,#0ea5e9,#22c55e);width:0}.flow h2{font-size:18px;margin:0 0 10px}.tabs{display:flex;gap:7px;overflow:auto;padding-bottom:7px}.tab{border:1px solid #334155;background:#182235;color:#e2e8f0;padding:9px 11px;border-radius:10px;white-space:nowrap;font-weight:700}.tab.active{background:#075985;border-color:#0ea5e9}.tablebox{border:1px solid var(--line);background:#111827;border-radius:14px;overflow:hidden}.tablewrap{overflow:auto;max-height:52vh}table{width:100%;border-collapse:collapse;min-width:900px}th{position:sticky;top:0;background:#182235;color:#cbd5e1;text-align:left;font-size:12px;padding:10px;border-bottom:1px solid #334155}th.sortable{cursor:pointer;user-select:none;white-space:nowrap}th.sortable:hover{background:#22304a;color:#f8fafc}.sortmark{display:inline-block;min-width:12px;margin-left:4px;color:#7dd3fc;font-size:10px}td{padding:10px;border-bottom:1px solid #1f2937;font-size:13px;white-space:nowrap}.empty{text-align:center;padding:30px;color:var(--muted)}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}.dot.prod{background:#f59e0b}.dot.ready{background:#22c55e}.dot.deliv{background:#38bdf8}.install{display:none;width:100%;border:1px solid #0369a1;background:#082f49;color:#bae6fd;padding:10px;border-radius:11px;margin-bottom:12px;font-weight:800}.install.show{display:block}@media(max-width:720px){.wrap{padding:13px}.grid{grid-template-columns:repeat(2,1fr)}.value{font-size:26px}.card{padding:13px}.top h1{font-size:19px}}
</style></head><body><main class="wrap">
<div class="top"><div><h1>Paleologos Production</h1><div class="sub">Απομακρυσμένη προβολή παραγωγής</div></div><div class="right"><span class="badge">READ ONLY</span><a class="logout" href="/logout">Έξοδος</a></div></div>
<button id="installBtn" class="install">⬇ Εγκατάσταση εφαρμογής</button>
<div id="sync" class="sync">Αναμονή συγχρονισμού από το εργοστάσιο...</div>
<section class="grid">
<div class="card"><div class="label">Πρόγραμμα σήμερα</div><div class="value" id="scheduled">—</div></div>
<div class="card"><div class="label">Σε παραγωγή σήμερα</div><div class="value" id="workload">—</div></div>
<div class="card"><div class="label">Παρήχθησαν σήμερα</div><div class="value green" id="produced">—</div></div>
<div class="card"><div class="label">Παραδόθηκαν σήμερα</div><div class="value green" id="delivered">—</div></div>
<div class="card"><div class="label">Έτοιμα προς φόρτωση</div><div class="value amber" id="ready">—</div></div>
<div class="card"><div class="label">Καθυστερημένα παραγωγής</div><div class="value red" id="overdue">—</div></div>
</section>
<section class="progress"><div class="progresshead"><span>Πρόοδος παραγωγής σήμερα</span><strong id="progressText">— / —</strong></div><div class="bar"><span id="progressBar"></span></div></section>
<section class="flow"><h2>Ροή Παραγωγής</h2><div class="tabs"><button class="tab active" data-key="in_production">Σε παραγωγή</button><button class="tab" data-key="ready">Έτοιμα</button><button class="tab" data-key="delivered">Παραδόθηκαν σήμερα</button><button class="tab" data-key="warehouse">Αποθήκη</button></div><div class="tablebox"><div id="table" class="tablewrap"><div class="empty">Δεν υπάρχουν δεδομένα.</div></div></div></section>
</main><script>
let snap=null,active='in_production',installPrompt=null;const sortState={in_production:null,ready:null,delivered:null,warehouse:null};const $=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function setText(id,v){$(id).textContent=v??'—'}
function render(){if(!snap?.available){$('sync').className='sync stale';$('sync').innerHTML='<strong>Χωρίς δεδομένα.</strong> Περιμένω sync από το εργοστάσιο.';return}let s=snap.snapshot.summary||{},age=snap.age_seconds??0;$('sync').className='sync '+(age<120?'ok':'stale');$('sync').innerHTML=`<strong>${age<120?'LIVE':'Τελευταίο sync'}</strong> — ${esc(snap.snapshot.generated_at||'')} · ${Math.round(age)}s πριν`;setText('scheduled',s.scheduled_today);setText('workload',s.mobile_workload_today??s.remaining_today);setText('produced',s.produced_today);setText('delivered',s.delivered_today);setText('ready',s.ready_waiting);setText('overdue',s.overdue);let done=s.mobile_completed_today??s.completed_today_program??0,work=s.mobile_workload_today??s.scheduled_today??0,pct=Math.max(0,Math.min(100,Number(s.mobile_progress_pct??s.progress_pct??0)));$('progressText').textContent=`${done} / ${work} — ${Math.round(pct)}%`;$('progressBar').style.width=pct+'%';renderTable()}
function lastStatusTime(r){let fallback=r?.production_status==='DELIVERED'?r?.delivered_at:r?.ready_at;return r?.last_status_at||fallback||'-'}
function statusLabel(){return active==='in_production'?'Σε παραγωγή':active==='delivered'?'Παραδόθηκε':'Έτοιμο'}
function sortValue(r,key){if(key==='status')return statusLabel();if(key==='type')return r.mattress_type||r.product_category||'';if(key==='dimension')return `${r.width_cm??''} × ${r.length_cm??''}`;if(key==='last_status')return lastStatusTime(r);return r[key]??''}
function sortedRows(rows){let state=sortState[active];if(!state)return rows.slice();return rows.slice().sort((a,b)=>{let av=sortValue(a,state.key),bv=sortValue(b,state.key);let cmp=String(av).localeCompare(String(bv),'el',{numeric:true,sensitivity:'base'});return state.dir==='asc'?cmp:-cmp})}
function sortHeader(label,key){let state=sortState[active],mark=state?.key===key?(state.dir==='asc'?'▲':'▼'):'';return `<th class="sortable" data-sort="${key}">${label}<span class="sortmark">${mark}</span></th>`}
function setSort(key){let current=sortState[active];sortState[active]=current?.key===key?{key,dir:current.dir==='asc'?'desc':'asc'}:{key,dir:'asc'};renderTable()}
function renderTable(){let rows=snap?.snapshot?.flow?.[active]||[];if(!rows.length){$('table').innerHTML='<div class="empty">Δεν υπάρχουν εγγραφές.</div>';return}rows=sortedRows(rows);let dot=active==='in_production'?'prod':active==='ready'||active==='warehouse'?'ready':'deliv';let head='<table><thead><tr>'+sortHeader('Κατάσταση','status')+sortHeader('Πελάτης','customer')+sortHeader('Όνομα','retail_name')+sortHeader('Τύπος','type')+sortHeader('Διάσταση','dimension')+sortHeader('Ημ. Παραγωγής','production_date')+sortHeader('Barcode','unique_code')+sortHeader('Τελευταία ώρα','last_status')+'</tr></thead><tbody>';let body=rows.map(r=>`<tr><td><span class="dot ${dot}"></span>${statusLabel()}</td><td>${esc(r.customer)}</td><td>${esc(r.retail_name)}</td><td>${esc(r.mattress_type||r.product_category)}</td><td>${esc(r.width_cm)} × ${esc(r.length_cm)}</td><td>${esc(r.production_date)}</td><td>${esc(r.unique_code)}</td><td>${esc(lastStatusTime(r))}</td></tr>`).join('');$('table').innerHTML=head+body+'</tbody></table>';$('table').querySelectorAll('th[data-sort]').forEach(th=>th.addEventListener('click',()=>setSort(th.dataset.sort)))}
async function load(){try{let r=await fetch('/api/snapshot',{cache:'no-store'});if(r.status===401){location='/login';return}snap=await r.json();render()}catch(e){$('sync').className='sync stale';$('sync').innerHTML='<strong>Δεν υπάρχει σύνδεση.</strong>'}}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');active=b.dataset.key;renderTable()}));
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('installBtn').classList.add('show')});$('installBtn').addEventListener('click',async()=>{if(!installPrompt)return;installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;$('installBtn').classList.remove('show')});if('serviceWorker' in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('/static/sw.js'));
load();setInterval(load,5000);
</script></body></html>'''


def _configured():
    return bool(SYNC_TOKEN and DASHBOARD_PASSWORD)


def _logged_in():
    return bool(session.get("ok"))


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not _logged_in():
            if request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped


@app.get("/health")
def health():
    return {"status": "ok", "configured": _configured()}


@app.route("/login", methods=["GET", "POST"])
def login():
    if _logged_in():
        return redirect(url_for("index"))
    error = False
    if request.method == "POST" and DASHBOARD_PASSWORD:
        candidate = request.form.get("password", "")
        if hmac.compare_digest(candidate, DASHBOARD_PASSWORD):
            session.clear()
            session["ok"] = True
            return redirect(url_for("index"))
        error = True
    return render_template_string(LOGIN_HTML, error=error, setup=not bool(DASHBOARD_PASSWORD))


@app.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.get("/")
@login_required
def index():
    return DASHBOARD_HTML


@app.post("/api/sync")
def api_sync():
    if not SYNC_TOKEN:
        return jsonify({"error": "sync_not_configured"}), 503
    auth = request.headers.get("Authorization", "")
    expected = "Bearer " + SYNC_TOKEN
    if not hmac.compare_digest(auth, expected):
        return jsonify({"error": "unauthorized"}), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("summary"), dict) or not isinstance(data.get("flow"), dict):
        return jsonify({"error": "invalid_snapshot"}), 400
    received = datetime.now(timezone.utc)
    global _latest_snapshot, _received_at
    with _snapshot_lock:
        _latest_snapshot = data
        _received_at = received
    return jsonify({"ok": True, "received_at": received.isoformat(timespec="seconds")})


@app.get("/api/snapshot")
@login_required
def api_snapshot():
    with _snapshot_lock:
        snap = _latest_snapshot
        received = _received_at
    if snap is None:
        return jsonify({"available": False})
    now = datetime.now(timezone.utc)
    age = max(0.0, (now - received).total_seconds()) if received else None
    return jsonify({"available": True, "age_seconds": age, "server_received_at": received.isoformat(timespec="seconds") if received else None, "snapshot": snap})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
