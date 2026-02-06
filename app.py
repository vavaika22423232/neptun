import subprocess
import sys
import os
import signal
import time

def log(msg):
    print(f"[SUPERVISOR] {msg}", flush=True)

def main():
    log("🚀 Starting Neptun (Monolith Mode - no Redis required)...")
    
    port = os.environ.get("PORT", "10000")
    
    # Launch app_legacy via gunicorn (self-contained: Telegram + API in one process)
    web_cmd = [
        "gunicorn", "app_legacy:app",
        "--bind", f"0.0.0.0:{port}",
        "--workers", "2",
        "--worker-class", "gevent",
        "--worker-connections", "2000",
        "--timeout", "120",
        "--keep-alive", "5",
        "--access-logfile", "-"
    ]
    log(f"🔌 Launching: {' '.join(web_cmd)}")
    web_process = subprocess.Popen(web_cmd)
    
    def signal_handler(sig, frame):
        log("🛑 Shutting down...")
        try:
            web_process.terminate()
        except:
            pass
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        web_process.wait()
        code = web_process.returncode
        log(f"Process exited with code {code}")
        sys.exit(code)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
