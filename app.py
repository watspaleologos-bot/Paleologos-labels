import os
from flask import Flask, render_template_string

app = Flask(__name__)

HTML = """<!doctype html>
<html lang="el">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
  <meta name="theme-color" content="#0f172a">
  <link rel="manifest" href="/static/manifest.json">
  <title>Paleologos Production</title>
  <style>
    :root{--bg:#0b1220;--panel:#111827;--muted:#94a3b8;--text:#f8fafc;--ok:#22c55e;--warn:#f59e0b;--danger:#ef4444}
    *{box-sizing:border-box}
    body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:linear-gradient(180deg,#09111f,#0b1220);color:var(--text);min-height:100vh}
    .wrap{max-width:1180px;margin:auto;padding:18px}
    .top{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:18px}
    .brand h1{font-size:22px;margin:0}.brand p{color:var(--muted);margin:4px 0 0;font-size:13px}
    .badge{background:#172554;color:#bfdbfe;padding:7px 10px;border-radius:999px;font-size:12px;font-weight:700}
    .notice{background:#172033;border:1px solid #26364f;border-radius:14px;padding:12px 14px;color:#cbd5e1;font-size:13px;margin-bottom:16px}
    .notice strong{color:#fff}
    .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
    .card{background:rgba(17,24,39,.92);border:1px solid #253149;border-radius:16px;padding:16px;box-shadow:0 10px 30px rgba(0,0,0,.18)}
    .label{color:var(--muted);font-size:12px}.value{font-size:30px;font-weight:800;margin-top:6px}
    .value.ok{color:#86efac}.value.warn{color:#fcd34d}.value.danger{color:#fca5a5}
    .progress{margin:16px 0;background:#1e293b;border-radius:14px;padding:15px}
    .progress-head{display:flex;justify-content:space-between;font-size:13px;color:#cbd5e1}
    .bar{height:10px;background:#334155;border-radius:999px;overflow:hidden;margin-top:10px}
    .bar>span{display:block;height:100%;width:0;background:linear-gradient(90deg,#0ea5e9,#22c55e)}
    .section{margin-top:18px}.section h2{font-size:17px;margin:0 0 10px}
    .tabs{display:flex;gap:8px;overflow:auto;padding-bottom:6px}
    .tab{white-space:nowrap;background:#182235;border:1px solid #293750;padding:9px 12px;border-radius:10px;font-size:13px}
    .tab.active{background:#0c4a6e;border-color:#0369a1}
    .table{margin-top:10px;background:#111827;border:1px solid #253149;border-radius:14px;overflow:hidden}
    .empty{padding:34px 16px;text-align:center;color:var(--muted)}
    footer{color:#64748b;text-align:center;font-size:12px;padding:25px 0 8px}
    @media(max-width:720px){.wrap{padding:14px}.grid{grid-template-columns:repeat(2,1fr)}.card{padding:14px}.value{font-size:26px}.brand h1{font-size:19px}}
  </style>
</head>
<body>
  <main class="wrap">
    <div class="top">
      <div class="brand"><h1>Paleologos Production</h1><p>Απομακρυσμένη προβολή παραγωγής</p></div>
      <div class="badge">READ ONLY</div>
    </div>
    <div class="notice"><strong>Railway/PWA skeleton ενεργό.</strong> Δεν έχει συνδεθεί ακόμη με το τοπικό production.db, επομένως δεν εμφανίζονται πραγματικά δεδομένα.</div>
    <section class="grid">
      <div class="card"><div class="label">Πρόγραμμα σήμερα</div><div class="value">—</div></div>
      <div class="card"><div class="label">Σε παραγωγή σήμερα</div><div class="value">—</div></div>
      <div class="card"><div class="label">Παρήχθησαν σήμερα</div><div class="value ok">—</div></div>
      <div class="card"><div class="label">Παραδόθηκαν σήμερα</div><div class="value ok">—</div></div>
      <div class="card"><div class="label">Έτοιμα προς φόρτωση</div><div class="value warn">—</div></div>
      <div class="card"><div class="label">Καθυστερημένα παραγωγής</div><div class="value danger">—</div></div>
    </section>
    <section class="progress"><div class="progress-head"><span>Πρόοδος ημέρας</span><strong>— / —</strong></div><div class="bar"><span></span></div></section>
    <section class="section">
      <h2>Ροή Παραγωγής</h2>
      <div class="tabs"><div class="tab active">Σε παραγωγή</div><div class="tab">Έτοιμα</div><div class="tab">Παραδόθηκαν</div><div class="tab">Αποθήκη</div></div>
      <div class="table"><div class="empty">Η σύνδεση με το εργοστάσιο θα προστεθεί στο επόμενο στάδιο.</div></div>
    </section>
    <footer>Paleologos Production • Remote Dashboard</footer>
  </main>
  <script>
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => navigator.serviceWorker.register('/static/sw.js'));
    }
  </script>
</body>
</html>"""

@app.get("/")
def index():
    return render_template_string(HTML)

@app.get("/health")
def health():
    return {"status": "ok", "service": "paleologos-production"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
