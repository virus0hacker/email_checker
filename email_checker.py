#!/usr/bin/env python3
import sys, os, re, time, json, urllib.request, urllib.error, urllib.parse
from datetime import datetime

if sys.platform == "win32":
    os.system("color")

R   = "\033[91m"
G   = "\033[92m"
Y   = "\033[93m"
B   = "\033[94m"
C   = "\033[96m"
W   = "\033[97m"
DIM = "\033[2m"
BO  = "\033[1m"
RS  = "\033[0m"

XON_API       = "https://api.xposedornot.com/v1"
HACKCHECK_API = "https://hackcheck.woventeams.com/api/v4"


def clr(text, color, bold=False):
    return f"{BO if bold else ''}{color}{text}{RS}"


def plain(text):
    return re.sub(r'\033\[[0-9;]*m', '', text)


def validate_email(email):
    return bool(re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email))


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "EmailChecker/4.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode())
        except:
            body = {}
        return e.code, body
    except Exception as e:
        return 0, {"error": str(e)}


def spinner(label, duration=1.2):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    end = time.time() + duration
    i = 0
    while time.time() < end:
        sys.stdout.write(f"\r  {clr(frames[i % len(frames)], C)}  {label}")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 70 + "\r")
    sys.stdout.flush()


# ─── Report buffer ────────────────────────────────────────────────────────────

report_lines = []

def out(line=""):
    print(line)
    report_lines.append(plain(line))

def save_report(email):
    safe     = re.sub(r'[^\w@._-]', '_', email)
    ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{safe}_{ts}.txt"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath   = os.path.join(script_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    print(clr(f"\n  ✔  Report saved → {filename}", G, bold=True))
    print()
    return filepath


# ─── UI ───────────────────────────────────────────────────────────────────────

def banner():
    print()
    print(clr("  ╔════════════════════════════════════════════════════════╗", C, bold=True))
    print(clr("  ║  ", C, bold=True) + clr("                  EMAIL CHECKER                  ", W, bold=True) + clr("  ║", C, bold=True))
    print(clr("  ╠════════════════════════════════════════════════════════╣", C, bold=True))
    print(clr("  ║  ", C, bold=True) + clr("  Author  :  ", DIM) + clr("ViRuS-HaCkEr", R, bold=True) + clr("                               ", DIM) + clr("  ║", C, bold=True))
    print(clr("  ║  ", C, bold=True) + clr("  Snap    :  ", DIM) + clr("ml-ftt", Y, bold=True)       + clr("                                    ", DIM) + clr("  ║", C, bold=True))
    print(clr("  ╚════════════════════════════════════════════════════════╝", C, bold=True))
    print()


def divider():
    out(clr("  " + "─" * 56, DIM))


def pw_color(risk):
    r = (risk or "").lower()
    if "plain" in r: return R
    if "hash"  in r: return Y
    return DIM


# ─── Breach card ─────────────────────────────────────────────────────────────

def print_card(b, index):
    name     = b.get("Breach ID",        b.get("Title", b.get("Name", "Unknown")))
    domain   = b.get("Domain",           "")
    date     = b.get("Breached Date",    b.get("BreachDate", ""))
    records  = b.get("Exposed Records",  b.get("PwnCount", 0))
    industry = b.get("Industry",         "")
    exposed  = b.get("Exposed Data",     "")
    pw_risk  = b.get("Password Risk",    "")
    verified = b.get("Verified",         b.get("IsVerified", ""))
    sensitive= b.get("Sensitive",        b.get("IsSensitive", False))

    if isinstance(date, str) and "T" in date:
        date = date.split("T")[0]

    icon = clr("✔", G) if verified in (True,"Yes","true") else clr("~", Y)
    sens = clr("  ⚠ SENSITIVE", R, bold=True) if sensitive in (True,"Yes") else ""

    out(f"  {icon}  {clr(f'[{index}]', DIM)} {clr(name, W, bold=True)}{sens}")
    if domain and domain.lower() not in ("","n/a","not-applicable"):
        out(f"  {clr('│', DIM)}  {clr('Domain   :', DIM)} {clr(domain, C)}")
    if date:
        out(f"  {clr('│', DIM)}  {clr('Date     :', DIM)} {clr(date, Y)}")
    if records:
        out(f"  {clr('│', DIM)}  {clr('Records  :', DIM)} {clr(f'{int(records):,}', R)}")
    if industry:
        out(f"  {clr('│', DIM)}  {clr('Industry :', DIM)} {clr(industry, DIM)}")
    if exposed:
        items = [x.strip() for x in exposed.replace(";",",").split(",") if x.strip()]
        out(f"  {clr('│', DIM)}  {clr('Exposed  :', DIM)} {clr(', '.join(items[:8]), C)}")
    if pw_risk and pw_risk.lower() not in ("","unknown"):
        rc = pw_color(pw_risk)
        out(f"  {clr('│', DIM)}  {clr('PW Risk  :', DIM)} {clr(pw_risk.upper(), rc, bold=True)}")
    out(f"  {clr('└', DIM)}")


# ─── XposedOrNot ─────────────────────────────────────────────────────────────

def check_xon(email):
    spinner("XposedOrNot — scanning breach records ...", 1.5)

    # Try breach-analytics first (full details)
    code, data = http_get(f"{XON_API}/breach-analytics?email={urllib.parse.quote(email)}")

    out(f"  {clr('[ SOURCE 1 — XposedOrNot ]', B, bold=True)}")
    out()

    if code == 200 and isinstance(data, dict) and data.get("status") == "success":
        details = data.get("ExposedBreaches", {}).get("breaches_details", [])
        summary = data.get("BreachesSummary", {}).get("site", [])
        metrics = data.get("BreachMetrics",   {})
        pastes  = data.get("ExposedPastes",   {})

        all_breaches = details if details else []
        count = len(all_breaches) if all_breaches else len(summary)

        if count == 0 and not summary:
            out(f"  {clr('✔', G, bold=True)}  No breaches found.")
            out()
            return 0

        out(f"  {clr('✘', R, bold=True)}  Found in {clr(str(count), R, bold=True)} breach(es):")
        out()

        if all_breaches:
            for i, b in enumerate(all_breaches, 1):
                print_card(b, i)
        elif summary:
            for i, name in enumerate(summary, 1):
                out(f"  {clr('→', Y)}  {clr(f'[{i}]', DIM)} {clr(str(name), W, bold=True)}")
                out(f"  {clr('└', DIM)}")

        # Metrics summary
        if metrics:
            risk_score = metrics.get("risk_score", "")
            pw_types   = metrics.get("passwords_strength", {})
            if risk_score:
                rc = R if float(str(risk_score)) >= 7 else Y
                out(f"  {clr('Risk Score :', DIM)} {clr(str(risk_score) + ' / 10', rc, bold=True)}")
            if pw_types and isinstance(pw_types, dict):
                types_str = "  |  ".join([f"{k}: {v}" for k,v in pw_types.items()])
                out(f"  {clr('PW Types   :', DIM)} {clr(types_str, Y)}")
            out()

        # Pastes
        paste_list = pastes.get("pastes_details", []) if isinstance(pastes, dict) else []
        if paste_list:
            out(f"  {clr('[ PASTES ]', Y, bold=True)}")
            for p in paste_list[:5]:
                src  = p.get("Source", "Unknown")
                date = p.get("Date",   "N/A")
                out(f"  {clr('→', Y)}  {clr(src, W)}  {clr(str(date), DIM)}")
            out()

        return count

    elif code == 404:
        out(f"  {clr('✔', G, bold=True)}  No breaches found.")
        out()
        return 0
    else:
        out(f"  {clr('!', Y)}  XposedOrNot returned HTTP {code} — {data}")
        out()
        return -1


# ─── HackCheck ───────────────────────────────────────────────────────────────

def check_hackcheck(email):
    spinner("HackCheck — cross-referencing breach database ...", 1.5)
    code, data = http_get(f"{HACKCHECK_API}/breachedaccount/{urllib.parse.quote(email)}")

    out(f"  {clr('[ SOURCE 2 — HackCheck ]', B, bold=True)}")
    out()

    if code == 200 and isinstance(data, list) and len(data) > 0:
        out(f"  {clr('✘', R, bold=True)}  Found in {clr(str(len(data)), R, bold=True)} breach(es):")
        out()
        for i, b in enumerate(data, 1):
            classes = b.get("DataClasses", [])
            mapped = {
                "Breach ID"      : b.get("Title",       b.get("Name", "Unknown")),
                "Domain"         : b.get("Domain",       ""),
                "Breached Date"  : b.get("BreachDate",   ""),
                "Exposed Records": b.get("PwnCount",     0),
                "Exposed Data"   : ", ".join(classes),
                "Verified"       : b.get("IsVerified",   False),
                "Sensitive"      : b.get("IsSensitive",  False),
            }
            print_card(mapped, i)
        return len(data)

    elif code == 404 or (code == 200 and isinstance(data, list) and len(data) == 0):
        out(f"  {clr('✔', G, bold=True)}  No breaches found.")
        out()
        return 0
    else:
        out(f"  {clr('!', Y)}  HackCheck returned HTTP {code}")
        out()
        return -1


# ─── Run ─────────────────────────────────────────────────────────────────────

def run_check(email):
    report_lines.clear()

    divider()
    out(f"\n  {clr('Target  :', B)}  {clr(email, W, bold=True)}")
    out(f"  {clr('Time    :', B)}  {clr(datetime.now().strftime('%Y-%m-%d  %H:%M:%S'), DIM)}")
    out()

    if not validate_email(email):
        out(f"  {clr('✘', R, bold=True)}  Invalid email format.")
        out()
        return

    r1 = check_xon(email)
    time.sleep(1.5)
    r2 = check_hackcheck(email)

    divider()
    out()

    total = max(r1, 0) + max(r2, 0)
    if total > 0:
        out(f"  {clr('⚠  RESULT:', R, bold=True)} Found in {clr(str(total), R, bold=True)} breach(es). Change your passwords!")
        out()
        out(f"  {clr('NOTE:', Y, bold=True)} Breach databases show WHICH sites leaked your data.")
        out(f"  {clr('     ', Y)} Actual plaintext passwords are never stored publicly.")
        out(f"  {clr('     ', Y)} If PW Risk = PLAINTEXT your password was fully exposed.")
    elif r1 == 0 and r2 == 0:
        out(f"  {clr('✓  RESULT:', G, bold=True)} Email not found in any known breach database.")
    else:
        out(f"  {clr('~  RESULT:', Y, bold=True)} Check completed — some sources unavailable.")

    out()
    save_report(email)


def usage():
    print(f"  {clr('Usage:', W, bold=True)}")
    print(f"    python {sys.argv[0]} <email>")
    print(f"    python {sys.argv[0]} emails.txt")
    print()


def main():
    banner()
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)

    target = sys.argv[1]
    try:
        with open(target, "r") as f:
            emails = [l.strip() for l in f if l.strip()]
        print(clr(f"  Loaded {len(emails)} emails from file.\n", C))
        for email in emails:
            run_check(email)
            time.sleep(3)
    except FileNotFoundError:
        run_check(target)


if __name__ == "__main__":
    main()
