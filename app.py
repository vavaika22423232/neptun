import subprocess
import sys
import os
import signal
import time

def log(msg):
    print(f"[SUPERVISOR] {msg}", flush=True)

def main():
    log("🚀 Starting Neptun v2.0 (Dual Activity Mode)...")
    
    # 1. Start Web API (Gunicorn)
    # Render provides PORT env var
    port = os.environ.get("PORT", "10000")
    # Use 4 workers for Pro Ultra instance (8 CPU) to utilize cores, but leave room for Worker
    web_cmd = ["gunicorn", "api:app", "--bind", f"0.0.0.0:{port}", "--workers", "4", "--timeout", "120", "--access-logfile", "-"]
    log(f"🔌 Launching Web API: {' '.join(web_cmd)}")
    web_process = subprocess.Popen(web_cmd)
    
    # 2. Start Worker (Parser)
    # Parser is async, single process usually enough, but heavy regex might benefit from isolated process
    worker_cmd = [sys.executable, "worker.py"]
    log(f"🤖 Launching Worker: {' '.join(worker_cmd)}")
    worker_process = subprocess.Popen(worker_cmd)
    
    def signal_handler(sig, frame):
        log("🛑 Shutting down...")
        try:
            web_process.terminate()
            worker_process.terminate()
        except:
            pass
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    try:
        while True:
            if web_process.poll() is not None:
                log(f"❌ Web API process ended. Shutting down supervisor.")
                try: worker_process.terminate()
                except: pass
                sys.exit(1)
            if worker_process.poll() is not None:
                log(f"❌ Worker process ended. Shutting down supervisor.")
                try: web_process.terminate()
                except: pass
                sys.exit(1)
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()
