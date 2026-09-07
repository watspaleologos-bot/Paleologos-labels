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
    # A fresh Railway process may receive a one-time history rebuild from the local
    # PC. Normal syncs remain tiny deltas, but the rebuild must have comfortable room.
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
)

_snapshot_lock = threading.Lock()
_latest_snapshot = None
_received_at = None

# Read-only canonical activity mirror keyed by barcode. It is intentionally in
# memory: the factory PC remains source of truth and automatically rebuilds this
# mirror after a Railway restart by using the status-event cursor handshake.
_activity_by_code: dict[str, dict] = {}
_history_cursor = 0
_history_initialized = False

LOGIN_HTML = r'''<!doctype html><html lang="el"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#0f172a"><title>Paleologos Production</title><style>*{box-sizing:border-box}body{margin:0;background:#08111f;color:#f8fafc;font-family:system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh;display:grid;place-items:center;padding:20px}.box{width:min(430px,100%);background:#111827;border:1px solid #26344d;border-radius:20px;padding:24px;box-shadow:0 24px 70px #0006}h1{margin:0 0 5px;font-size:24px}p{color:#94a3b8;margin:0 0 20px}input,button{width:100%;min-height:50px;border-radius:12px;font-size:16px}input{background:#0f172a;color:#fff;border:1px solid #334155;padding:12px 14px;margin-bottom:10px}button{border:0;background:#0ea5e9;color:white;font-weight:800}.err{background:#450a0a;color:#fecaca;border:1px solid #7f1d1d;padding:10px 12px;border-radius:10px;margin-bottom:12px}.small{font-size:12px;color:#64748b;margin-top:14px}</style></head><body><form class="box" method="post"><h1>Paleologos Production</h1><p>Απομακρυσμένη προβολή παραγωγής</p>{% if setup %}<div class="err">Δεν έχει οριστεί DASHBOARD_PASSWORD στο Railway.</div>{% elif error %}<div class="err">Λάθος κωδικός.</div>{% endif %}<input name="password" type="password" placeholder="Κωδικός πρόσβασης" autocomplete="current-password" {% if setup %}disabled{% endif %}><button type="submit" {% if setup %}disabled{% endif %}>Σύνδεση</button><div class="small">Read-only dashboard</div></form></body></html>'''

DASHBOARD_HTML = r'''<!doctype html>
<html lang="el"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#0f172a"><meta name="mobile-web-app-capable" content="yes">
<link rel="manifest" href="/static/manifest.json"><link rel="icon" href="/static/icon-192.png?v=191"><link rel="apple-touch-icon" href="/static/icon-192.png?v=191"><title>Paleologos Production</title>
<style>
:root{--bg:#09111f;--panel:#111827;--line:#26344d;--muted:#94a3b8;--text:#f8fafc;--blue:#0ea5e9;--green:#22c55e;--amber:#f59e0b;--red:#ef4444;--delivery:#38bdf8}
*{box-sizing:border-box}body{margin:0;background:linear-gradient(180deg,#08111f,#0b1220);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}.wrap{max-width:1220px;margin:auto;padding:16px}.top{display:flex;justify-content:space-between;align-items:flex-start;gap:10px;margin-bottom:14px}.top h1{font-size:22px;margin:0}.sub{color:var(--muted);font-size:13px;margin-top:3px}.right{display:flex;align-items:center;gap:8px}.badge{background:#172554;color:#bfdbfe;border-radius:999px;padding:7px 10px;font-size:11px;font-weight:800}.logout{color:#cbd5e1;text-decoration:none;font-size:12px}.sync{background:#111827;border:1px solid var(--line);border-radius:13px;padding:11px 13px;margin-bottom:14px;color:#cbd5e1;font-size:13px}.sync.ok strong{color:#86efac}.sync.stale strong{color:#fde68a}.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.card{background:rgba(17,24,39,.94);border:1px solid var(--line);border-radius:16px;padding:15px}.label{font-size:12px;color:var(--muted)}.value{font-size:29px;font-weight:850;margin-top:5px}.green{color:#86efac}.amber{color:#fcd34d}.red{color:#fca5a5}.progress{margin:12px 0 18px;background:#172033;border:1px solid var(--line);border-radius:14px;padding:14px}.progresshead{display:flex;justify-content:space-between;color:#cbd5e1;font-size:13px}.bar{height:9px;background:#334155;border-radius:99px;overflow:hidden;margin-top:9px}.bar span{display:block;height:100%;background:linear-gradient(90deg,#0ea5e9,#22c55e);width:0}.flow h2{font-size:18px;margin:0 0 10px}.tabs{display:flex;gap:7px;overflow:auto;padding-bottom:7px}.tab{border:1px solid #334155;background:#182235;color:#e2e8f0;padding:9px 11px;border-radius:10px;white-space:nowrap;font-weight:700}.tab.active{background:#075985;border-color:#0ea5e9}.tablebox{border:1px solid var(--line);background:#111827;border-radius:14px;overflow:hidden}.tablewrap{overflow:auto;max-height:52vh}table{width:100%;border-collapse:collapse;min-width:900px}th{position:sticky;top:0;background:#182235;color:#cbd5e1;text-align:left;font-size:12px;padding:10px;border-bottom:1px solid #334155}th.sortable{cursor:pointer;user-select:none;white-space:nowrap}th.sortable:hover{background:#22304a;color:#f8fafc}.sortmark{display:inline-block;min-width:12px;margin-left:4px;color:#7dd3fc;font-size:10px}td{padding:10px;border-bottom:1px solid #1f2937;font-size:13px;white-space:nowrap}.rownum{width:44px;text-align:center;color:#94a3b8;font-variant-numeric:tabular-nums}.empty{text-align:center;padding:30px;color:var(--muted)}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:6px}.dot.prod{background:#f59e0b}.dot.ready{background:#22c55e}.dot.deliv{background:#38bdf8}.install{display:none;width:100%;border:1px solid #0369a1;background:#082f49;color:#bae6fd;padding:10px;border-radius:11px;margin-bottom:12px;font-weight:800}.install.show{display:block}
.history{display:none}.history.show{display:block}.historyStatus{border:1px solid var(--line);background:#111827;border-radius:12px;padding:10px 12px;margin-bottom:9px;color:#cbd5e1;font-size:12px}.historyStatus.ok{color:#86efac}.calendarPanel{background:#111827;border:1px solid var(--line);border-radius:14px;padding:8px;margin-bottom:8px}.calHead{display:flex;align-items:center;justify-content:space-between;gap:6px;margin-bottom:4px}.calHead strong{font-size:14px}.calHead button{width:auto;min-height:32px;padding:5px 10px}.calHead input{width:auto;min-height:32px;background:#0f172a;color:#fff;border:1px solid #334155;border-radius:9px;padding:4px 7px}.calendar{display:grid;grid-template-columns:repeat(7,1fr);gap:3px}.dow{text-align:center;color:#94a3b8;font-size:10px;font-weight:800;padding:2px}.day{min-height:40px;background:#0f172a;border:1px solid #26344d;border-radius:7px;padding:4px;cursor:pointer}.day:hover{border-color:#0ea5e9}.day.blank{background:#0b1220;cursor:default;opacity:.45}.day.future{cursor:default;color:#64748b}.day.future:hover{border-color:#26344d}.day.today{border:2px solid #0ea5e9}.dayNum{font-size:11px;font-weight:850;margin-bottom:3px}.dayCounts{display:flex;align-items:center;gap:6px;flex-wrap:wrap}.dayCount{display:inline-flex;align-items:center;font-size:10px;font-weight:850;line-height:1}.dayReady{color:#86efac}.dayDelivered{color:#7dd3fc}.miniDot{display:inline-block;width:7px;height:7px;border-radius:50%;margin-right:3px;flex:0 0 auto}.miniDot.ready{background:#22c55e}.miniDot.delivered{background:#38bdf8}.historyFilters{display:flex;gap:7px;flex-wrap:wrap;align-items:end;background:#111827;border:1px solid var(--line);border-radius:12px;padding:10px;margin-bottom:9px}.historyFilters label{display:flex;flex-direction:column;gap:4px;color:#94a3b8;font-size:11px}.historyFilters select,.historyFilters input{min-height:38px;background:#0f172a;color:#fff;border:1px solid #334155;border-radius:9px;padding:6px 9px}.historyFilters button{width:auto;min-height:38px;padding:7px 13px}.historyTotals{display:flex;gap:18px;flex-wrap:wrap;margin:3px 3px 9px;font-size:13px;font-weight:850}.historyTotals .r{color:#86efac}.historyTotals .d{color:#7dd3fc}.historyTable .tablewrap{max-height:48vh}.eventReady{color:#86efac;font-weight:800}.eventDelivered{color:#7dd3fc;font-weight:800}
button{border:0;background:#0ea5e9;color:white;font-weight:800;border-radius:10px}@media(max-width:720px){.wrap{padding:13px}.grid{grid-template-columns:repeat(2,1fr)}.value{font-size:26px}.card{padding:13px}.top h1{font-size:19px}.calendarPanel{padding:7px}.calHead{gap:4px;margin-bottom:3px}.calHead strong{font-size:12px}.calHead button{min-height:28px;padding:4px 8px}.calHead input{min-height:28px;padding:3px 5px;font-size:12px}.calendar{gap:2px}.dow{font-size:9px;padding:1px}.day{min-height:34px;padding:3px;border-radius:6px}.dayNum{font-size:10px;margin-bottom:2px}.dayCounts{gap:4px}.dayCount{font-size:9px}.miniDot{width:6px;height:6px;margin-right:2px}.historyFilters{align-items:stretch}.historyFilters label{min-width:46%}}
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
<section class="flow"><h2>Ροή Παραγωγής</h2><div class="tabs"><button class="tab active" data-key="in_production">Σε παραγωγή</button><button class="tab" data-key="ready">Έτοιμα</button><button class="tab" data-key="delivered">Παραδόθηκαν σήμερα</button><button class="tab" data-key="warehouse">Αποθήκη</button><button class="tab" data-key="history">Ιστορικό</button></div><div id="flowTableBox" class="tablebox"><div id="table" class="tablewrap"><div class="empty">Δεν υπάρχουν δεδομένα.</div></div></div>
<div id="historyPanel" class="history">
  <div id="historyStatus" class="historyStatus">Το ιστορικό συγχρονίζεται από το εργοστάσιο.</div>
  <div class="calendarPanel"><div class="calHead"><button id="prevMonth">◀</button><strong>Ημερολόγιο παραγωγής</strong><input id="monthPick" type="month"><button id="nextMonth">▶</button></div><div id="calendar" class="calendar"></div></div>
  <div class="historyFilters">
    <label>Περίοδος<select id="historyMode"><option value="day">Ημέρα</option><option value="month" selected>Μήνας</option><option value="year">Έτος</option><option value="range">Από - Έως</option><option value="all">Όλα</option></select></label>
    <label>Από<input id="historyFrom" type="date"></label><label>Έως<input id="historyTo" type="date"></label>
    <label>Κίνηση<select id="historyType"><option value="ALL">Όλα</option><option value="READY">Έτοιμα</option><option value="DELIVERED">Παραδόθηκαν</option></select></label>
    <button id="applyHistory">Εφαρμογή</button>
  </div>
  <div class="historyTotals"><span class="r" id="readyTotal">Έτοιμα: 0</span><span class="d" id="deliveredTotal">Παραδόθηκαν: 0</span></div>
  <div class="tablebox historyTable"><div id="historyTable" class="tablewrap"><div class="empty">Δεν υπάρχουν εγγραφές.</div></div></div>
</div></section>
</main><script>
let snap=null,active='in_production',installPrompt=null;const sortState={in_production:null,ready:null,delivered:null,warehouse:null};let historyRows=[],historySort={key:'event_at',dir:'desc'},historyCursorSeen=null;let historyMonth=new Date();historyMonth=new Date(historyMonth.getFullYear(),historyMonth.getMonth(),1);const $=id=>document.getElementById(id);const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function setText(id,v){$(id).textContent=v??'—'}function isoDate(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`}function monthStart(d){return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-01`}function monthEnd(d){return isoDate(new Date(d.getFullYear(),d.getMonth()+1,0))}
function render(){if(!snap?.available){$('sync').className='sync stale';$('sync').innerHTML='<strong>Χωρίς δεδομένα.</strong> Περιμένω sync από το εργοστάσιο.';return}let s=snap.snapshot.summary||{},age=snap.age_seconds??0;$('sync').className='sync '+(age<120?'ok':'stale');$('sync').innerHTML=`<strong>${age<120?'LIVE':'Τελευταίο sync'}</strong> — ${esc(snap.snapshot.generated_at||'')} · ${Math.round(age)}s πριν`;setText('scheduled',s.scheduled_today);setText('workload',s.mobile_workload_today??s.remaining_today);setText('produced',s.produced_today);setText('delivered',s.delivered_today);setText('ready',s.ready_waiting);setText('overdue',s.overdue);let done=s.mobile_completed_today??s.completed_today_program??0,work=s.mobile_workload_today??s.scheduled_today??0,pct=Math.max(0,Math.min(100,Number(s.mobile_progress_pct??s.progress_pct??0)));$('progressText').textContent=`${done} / ${work} — ${Math.round(pct)}%`;$('progressBar').style.width=pct+'%';if(active!=='history')renderTable();else if(historyCursorSeen!==snap.history_cursor){historyCursorSeen=snap.history_cursor;refreshHistory(true)}}
function lastStatusTime(r){let fallback=r?.production_status==='DELIVERED'?r?.delivered_at:r?.ready_at;return r?.last_status_at||fallback||'-'}function statusLabel(){return active==='in_production'?'Σε παραγωγή':active==='delivered'?'Παραδόθηκε':'Έτοιμο'}function sortValue(r,key){if(key==='status')return statusLabel();if(key==='type')return r.mattress_type||r.product_category||'';if(key==='dimension')return `${r.width_cm??''} × ${r.length_cm??''}`;if(key==='last_status')return lastStatusTime(r);return r[key]??''}function sortedRows(rows){let state=sortState[active];if(!state)return rows.slice();return rows.slice().sort((a,b)=>{let av=sortValue(a,state.key),bv=sortValue(b,state.key);let cmp=String(av).localeCompare(String(bv),'el',{numeric:true,sensitivity:'base'});return state.dir==='asc'?cmp:-cmp})}function sortHeader(label,key){let state=sortState[active],mark=state?.key===key?(state.dir==='asc'?'▲':'▼'):'';return `<th class="sortable" data-sort="${key}">${label}<span class="sortmark">${mark}</span></th>`}function setSort(key){let current=sortState[active];sortState[active]=current?.key===key?{key,dir:current.dir==='asc'?'desc':'asc'}:{key,dir:'asc'};renderTable()}
function renderTable(){let rows=snap?.snapshot?.flow?.[active]||[];if(!rows.length){$('table').innerHTML='<div class="empty">Δεν υπάρχουν εγγραφές.</div>';return}rows=sortedRows(rows);let dot=active==='in_production'?'prod':active==='ready'||active==='warehouse'?'ready':'deliv';let head='<table><thead><tr><th class="rownum">#</th>'+sortHeader('Κατάσταση','status')+sortHeader('Πελάτης','customer')+sortHeader('Όνομα','retail_name')+sortHeader('Τύπος','type')+sortHeader('Διάσταση','dimension')+sortHeader('Ημ. Παραγωγής','production_date')+sortHeader('Barcode','unique_code')+sortHeader('Τελευταία ώρα','last_status')+'</tr></thead><tbody>';let body=rows.map((r,index)=>`<tr><td class="rownum">${index+1}</td><td><span class="dot ${dot}"></span>${statusLabel()}</td><td>${esc(r.customer)}</td><td>${esc(r.retail_name)}</td><td>${esc(r.mattress_type||r.product_category)}</td><td>${esc(r.width_cm)} × ${esc(r.length_cm)}</td><td>${esc(r.production_date)}</td><td>${esc(r.unique_code)}</td><td>${esc(lastStatusTime(r))}</td></tr>`).join('');$('table').innerHTML=head+body+'</tbody></table>';$('table').querySelectorAll('th[data-sort]').forEach(th=>th.addEventListener('click',()=>setSort(th.dataset.sort)))}
async function load(){try{let r=await fetch('/api/snapshot',{cache:'no-store'});if(r.status===401){location='/login';return}snap=await r.json();render()}catch(e){$('sync').className='sync stale';$('sync').innerHTML='<strong>Δεν υπάρχει σύνδεση.</strong>'}}
function setActive(key){active=key;document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.dataset.key===key));$('flowTableBox').style.display=key==='history'?'none':'block';$('historyPanel').classList.toggle('show',key==='history');if(key==='history'){prepareHistoryMonth();refreshHistory(true)}else renderTable()}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>setActive(b.dataset.key)));
function prepareHistoryMonth(){let value=`${historyMonth.getFullYear()}-${String(historyMonth.getMonth()+1).padStart(2,'0')}`;$('monthPick').value=value;if(!$('historyFrom').value)$('historyFrom').value=monthStart(historyMonth);if(!$('historyTo').value)$('historyTo').value=monthEnd(historyMonth)}
function applyMode(){let mode=$('historyMode').value;if(mode==='month'){$('historyFrom').value=monthStart(historyMonth);$('historyTo').value=monthEnd(historyMonth)}else if(mode==='year'){$('historyFrom').value=`${historyMonth.getFullYear()}-01-01`;$('historyTo').value=`${historyMonth.getFullYear()}-12-31`}else if(mode==='day'){let d=$('historyFrom').value||isoDate(new Date());$('historyFrom').value=d;$('historyTo').value=d}else if(mode==='all'){$('historyFrom').value='';$('historyTo').value=''}refreshHistory(false)}
function historyQuery(){let mode=$('historyMode').value,start=$('historyFrom').value,end=$('historyTo').value;if(mode==='month'){start=monthStart(historyMonth);end=monthEnd(historyMonth)}else if(mode==='year'){start=`${historyMonth.getFullYear()}-01-01`;end=`${historyMonth.getFullYear()}-12-31`}else if(mode==='day'){start=start||isoDate(new Date());end=start}else if(mode==='all'){start='';end=''}return {start,end,type:$('historyType').value}}
async function refreshHistory(includeCalendar){if(active!=='history')return;let q=historyQuery();if(q.start&&q.end&&q.start>q.end){$('historyStatus').className='historyStatus';$('historyStatus').textContent='Η ημερομηνία Από δεν μπορεί να είναι μετά την Έως.';return}try{let url='/api/history?type='+encodeURIComponent(q.type);if(q.start)url+='&start='+encodeURIComponent(q.start);if(q.end)url+='&end='+encodeURIComponent(q.end);let jobs=[fetch(url,{cache:'no-store'})];if(includeCalendar)jobs.push(fetch(`/api/calendar?year=${historyMonth.getFullYear()}&month=${historyMonth.getMonth()+1}`,{cache:'no-store'}));let responses=await Promise.all(jobs);if(responses[0].status===401){location='/login';return}let data=await responses[0].json();historyRows=data.rows||[];setText('readyTotal','Έτοιμα: '+(data.totals?.ready??0));setText('deliveredTotal','Παραδόθηκαν: '+(data.totals?.delivered??0));$('historyStatus').className='historyStatus '+(data.initialized?'ok':'');$('historyStatus').textContent=data.initialized?'Ιστορικό συγχρονισμένο με το εργοστάσιο.':'Συγχρονισμός ιστορικού από το εργοστάσιο...';renderHistoryTable();if(includeCalendar&&responses[1])renderCalendar(await responses[1].json())}catch(e){$('historyStatus').className='historyStatus';$('historyStatus').textContent='Δεν ήταν δυνατή η φόρτωση του ιστορικού.'}}
function renderCalendar(data){let counts=data.counts||{},year=Number(data.year),month=Number(data.month);let first=new Date(year,month-1,1),last=new Date(year,month,0),offset=(first.getDay()+6)%7,total=last.getDate(),todayKey=isoDate(new Date());let html=['Δευ','Τρι','Τετ','Πεμ','Παρ','Σαβ','Κυρ'].map(x=>`<div class="dow">${x}</div>`).join('');for(let i=0;i<42;i++){let day=i-offset+1;if(day<1||day>total){html+='<div class="day blank"></div>';continue}let key=`${year}-${String(month).padStart(2,'0')}-${String(day).padStart(2,'0')}`,isFuture=key>todayKey,today=key===todayKey?' today':'',future=isFuture?' future':'';if(isFuture){html+=`<div class="day${today}${future}"><div class="dayNum">${day}</div></div>`;continue}let c=counts[key]||{ready:0,delivered:0};html+=`<div class="day${today}" data-day="${key}"><div class="dayNum">${day}</div><div class="dayCounts"><span class="dayCount dayReady"><span class="miniDot ready"></span>${c.ready||0}</span><span class="dayCount dayDelivered"><span class="miniDot delivered"></span>${c.delivered||0}</span></div></div>`}$('calendar').innerHTML=html;$('calendar').querySelectorAll('.day[data-day]').forEach(el=>el.addEventListener('click',()=>{$('historyMode').value='day';$('historyFrom').value=el.dataset.day;$('historyTo').value=el.dataset.day;refreshHistory(false)}))}
function historySortValue(r,key){if(key==='type')return r.mattress_type||r.product_category||'';if(key==='dimension')return `${r.width_cm??''} × ${r.length_cm??''}`;return r[key]??''}function setHistorySort(key){historySort=historySort.key===key?{key,dir:historySort.dir==='asc'?'desc':'asc'}:{key,dir:'asc'};renderHistoryTable()}function hHead(label,key){let mark=historySort.key===key?(historySort.dir==='asc'?'▲':'▼'):'';return `<th class="sortable" data-hsort="${key}">${label}<span class="sortmark">${mark}</span></th>`}
function renderHistoryTable(){let rows=historyRows.slice().sort((a,b)=>{let av=historySortValue(a,historySort.key),bv=historySortValue(b,historySort.key),cmp=String(av).localeCompare(String(bv),'el',{numeric:true,sensitivity:'base'});return historySort.dir==='asc'?cmp:-cmp});if(!rows.length){$('historyTable').innerHTML='<div class="empty">Δεν υπάρχουν εγγραφές για το φίλτρο.</div>';return}let head='<table><thead><tr>'+hHead('Κίνηση','event_type')+hHead('Ημερομηνία / Ώρα','event_at')+hHead('Πελάτης','customer')+hHead('Όνομα','retail_name')+hHead('Τύπος','type')+hHead('Διάσταση','dimension')+hHead('Ημ. Παραγωγής','production_date')+hHead('Barcode','unique_code')+'</tr></thead><tbody>';let body=rows.map(r=>{let ready=r.event_type==='READY',label=ready?'Έτοιμο':'Παραδόθηκε',klass=ready?'eventReady':'eventDelivered';return `<tr><td class="${klass}">${label}</td><td>${esc(r.event_at)}</td><td>${esc(r.customer)}</td><td>${esc(r.retail_name)}</td><td>${esc(r.mattress_type||r.product_category)}</td><td>${esc(r.width_cm)} × ${esc(r.length_cm)}</td><td>${esc(r.production_date)}</td><td>${esc(r.unique_code)}</td></tr>`}).join('');$('historyTable').innerHTML=head+body+'</tbody></table>';$('historyTable').querySelectorAll('th[data-hsort]').forEach(th=>th.addEventListener('click',()=>setHistorySort(th.dataset.hsort)))}
$('historyMode').addEventListener('change',applyMode);$('historyType').addEventListener('change',()=>refreshHistory(false));$('applyHistory').addEventListener('click',()=>{$('historyMode').value='range';refreshHistory(false)});$('monthPick').addEventListener('change',()=>{let [y,m]=$('monthPick').value.split('-').map(Number);if(y&&m){historyMonth=new Date(y,m-1,1);if($('historyMode').value==='month')applyMode();refreshHistory(true)}});$('prevMonth').addEventListener('click',()=>{historyMonth=new Date(historyMonth.getFullYear(),historyMonth.getMonth()-1,1);prepareHistoryMonth();if($('historyMode').value==='month')applyMode();refreshHistory(true)});$('nextMonth').addEventListener('click',()=>{historyMonth=new Date(historyMonth.getFullYear(),historyMonth.getMonth()+1,1);prepareHistoryMonth();if($('historyMode').value==='month')applyMode();refreshHistory(true)});
window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();installPrompt=e;$('installBtn').classList.add('show')});$('installBtn').addEventListener('click',async()=>{if(!installPrompt)return;installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;$('installBtn').classList.remove('show')});if('serviceWorker' in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('/static/sw.js'));
prepareHistoryMonth();load();setInterval(load,5000);
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


def _valid_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def _apply_activity_units(units):
    global _activity_by_code
    if not isinstance(units, list):
        return
    for raw in units:
        if not isinstance(raw, dict):
            continue
        code = str(raw.get("unique_code") or "").strip()
        if not code:
            continue
        ready_at = raw.get("ready_at") or None
        delivered_at = raw.get("delivered_at") or None
        active = bool(raw.get("active", True))
        if not active or (not ready_at and not delivered_at):
            _activity_by_code.pop(code, None)
            continue
        _activity_by_code[code] = {
            "unique_code": code,
            "ready_at": ready_at,
            "delivered_at": delivered_at,
            "production_status": raw.get("production_status"),
            "production_date": raw.get("production_date"),
            "batch_number": raw.get("batch_number"),
            "customer": raw.get("customer"),
            "retail_name": raw.get("retail_name") or "",
            "product_category": raw.get("product_category"),
            "mattress_type": raw.get("mattress_type"),
            "width_cm": raw.get("width_cm"),
            "length_cm": raw.get("length_cm"),
        }


def _activity_rows(start=None, end=None, event_type="ALL"):
    normalized = str(event_type or "ALL").upper()
    if normalized not in {"ALL", "READY", "DELIVERED"}:
        normalized = "ALL"
    rows = []
    for unit in _activity_by_code.values():
        for kind, field in (("READY", "ready_at"), ("DELIVERED", "delivered_at")):
            if normalized not in {"ALL", kind}:
                continue
            stamp = str(unit.get(field) or "")
            if not stamp:
                continue
            day = stamp[:10]
            if start and day < start:
                continue
            if end and day > end:
                continue
            item = dict(unit)
            item["event_type"] = kind
            item["event_at"] = stamp
            rows.append(item)
    rows.sort(key=lambda row: (str(row.get("event_at") or ""), str(row.get("unique_code") or "")), reverse=True)
    return rows


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
    global _latest_snapshot, _received_at, _history_cursor, _history_initialized, _activity_by_code
    history_applied = False
    with _snapshot_lock:
        _latest_snapshot = data
        _received_at = received
        history = data.get("history_sync")
        if isinstance(history, dict):
            try:
                cursor_from = max(0, int(history.get("cursor_from", 0)))
                cursor_to = max(0, int(history.get("cursor_to", cursor_from)))
            except (TypeError, ValueError):
                cursor_from = _history_cursor
                cursor_to = _history_cursor
            reset = bool(history.get("reset"))
            if reset:
                _activity_by_code.clear()
                _apply_activity_units(history.get("units") or [])
                _history_cursor = cursor_to
                _history_initialized = True
                history_applied = True
            elif cursor_from == _history_cursor:
                _apply_activity_units(history.get("units") or [])
                _history_cursor = max(_history_cursor, cursor_to)
                _history_initialized = True
                history_applied = True

        current_history_cursor = _history_cursor
        initialized = _history_initialized

    return jsonify({
        "ok": True,
        "received_at": received.isoformat(timespec="seconds"),
        "history_cursor": current_history_cursor,
        "history_initialized": initialized,
        "history_applied": history_applied,
    })


@app.get("/api/snapshot")
@login_required
def api_snapshot():
    with _snapshot_lock:
        snap = _latest_snapshot
        received = _received_at
        history_cursor = _history_cursor
        history_initialized = _history_initialized
    if snap is None:
        return jsonify({"available": False, "history_cursor": history_cursor, "history_initialized": history_initialized})
    now = datetime.now(timezone.utc)
    age = max(0.0, (now - received).total_seconds()) if received else None
    return jsonify({
        "available": True,
        "age_seconds": age,
        "server_received_at": received.isoformat(timespec="seconds") if received else None,
        "snapshot": snap,
        "history_cursor": history_cursor,
        "history_initialized": history_initialized,
    })


@app.get("/api/history")
@login_required
def api_history():
    raw_start = request.args.get("start", "")
    raw_end = request.args.get("end", "")
    start = _valid_date(raw_start) if raw_start else None
    end = _valid_date(raw_end) if raw_end else None
    if raw_start and not start or raw_end and not end:
        return jsonify({"error": "invalid_date"}), 400
    if start and end and start > end:
        return jsonify({"error": "invalid_range"}), 400
    event_type = str(request.args.get("type", "ALL") or "ALL").upper()
    if event_type not in {"ALL", "READY", "DELIVERED"}:
        return jsonify({"error": "invalid_type"}), 400
    with _snapshot_lock:
        rows = _activity_rows(start, end, event_type)
        initialized = _history_initialized
        cursor = _history_cursor
    totals = {
        "ready": sum(1 for row in rows if row["event_type"] == "READY"),
        "delivered": sum(1 for row in rows if row["event_type"] == "DELIVERED"),
    }
    return jsonify({"initialized": initialized, "history_cursor": cursor, "rows": rows, "totals": totals})


@app.get("/api/calendar")
@login_required
def api_calendar():
    try:
        year = int(request.args.get("year", ""))
        month = int(request.args.get("month", ""))
    except (TypeError, ValueError):
        return jsonify({"error": "invalid_month"}), 400
    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        return jsonify({"error": "invalid_month"}), 400
    start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1:04d}-01-01"
    else:
        end = f"{year:04d}-{month + 1:02d}-01"
    counts = {}
    with _snapshot_lock:
        for unit in _activity_by_code.values():
            for kind, field in (("ready", "ready_at"), ("delivered", "delivered_at")):
                stamp = str(unit.get(field) or "")
                if not stamp or not (start <= stamp[:10] < end):
                    continue
                day = stamp[:10]
                counts.setdefault(day, {"ready": 0, "delivered": 0})[kind] += 1
        initialized = _history_initialized
        cursor = _history_cursor
    return jsonify({"initialized": initialized, "history_cursor": cursor, "year": year, "month": month, "counts": counts})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
