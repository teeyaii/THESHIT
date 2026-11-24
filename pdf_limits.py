"""Local PDF resource budgets and isolated worker dispatch (not a security sandbox)."""
import hashlib
import json
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

MAX_PDF_BYTES=50*1024*1024
MAX_SOURCE_PAGES=200
MAX_RESULT_BYTES=32*1024*1024
MAX_REQUEST_BYTES=2*1024*1024
MAX_MATCHES=500
MAX_PIXELS=20_000_000
OPERATIONS={"extract","atlas","matches"}

class ResourceLimitError(ValueError):
    """An explicit PDF resource budget was exceeded."""

def check_pdf(path):
    p=Path(path).resolve()
    if p.suffix.lower()!=".pdf" or not p.is_file():
        raise ValueError("Existing local PDF required")
    if not 0<p.stat().st_size<=MAX_PDF_BYTES:
        raise ResourceLimitError("Local PDF size limit exceeded or empty")
    return p

def stream_digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def checked_pages(pdf):
    pages=pdf.pages
    if not 0<len(pages)<=MAX_SOURCE_PAGES:
        raise ResourceLimitError("PDF page count outside supported budget")
    return pages

def check_raster(page,dpi):
    if not 0<(page.width*dpi/72)*(page.height*dpi/72)<=MAX_PIXELS:
        raise ResourceLimitError("PDF raster pixel limit exceeded")

def run_bounded(operation,kwargs,*,timeout=180):
    """Use a fresh process and kill its POSIX process group on timeout.
    Windows kills the direct worker only; not a sandbox or full memory isolation.
    """
    if operation not in OPERATIONS or not 0<timeout<=300:
        raise ValueError("Unsupported operation or wall-clock budget")
    payload=json.dumps({"operation":operation,"kwargs":kwargs},ensure_ascii=False,allow_nan=False).encode("utf-8")
    if len(payload)>MAX_REQUEST_BYTES:
        raise ResourceLimitError("PDF worker request limit exceeded")
    with tempfile.TemporaryDirectory(prefix="theshit-pdf-") as d:
        req=Path(d)/"request.json";result=Path(d)/"result.json"
        req.write_bytes(payload)
        proc=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),str(req),str(result)],
                              stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                              start_new_session=(os.name=="posix"))
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                if os.name=="posix":os.killpg(proc.pid,signal.SIGKILL)
                else:proc.kill()
            except ProcessLookupError:pass
            finally:proc.wait()
            raise ResourceLimitError("PDF worker wall-clock limit exceeded") from None
        if proc.returncode!=0 or not result.is_file():
            raise ValueError("PDF worker failed without a complete result")
        if result.stat().st_size>MAX_RESULT_BYTES:
            raise ResourceLimitError("PDF worker result limit exceeded")
        response=json.loads(result.read_text(encoding="utf-8"))
        if not response.get("ok"):
            cls=ResourceLimitError if response.get("error_type")=="ResourceLimitError" else ValueError
            raise cls(response.get("message","PDF worker failed"))
        return response["value"]

def worker(request_path,result_path):
    try:
        request=json.loads(Path(request_path).read_text(encoding="utf-8"))
        operation=request["operation"]
        if operation=="extract":
            from pdf_text_engine import _extract_pdf as operation_fn
        elif operation=="atlas":
            from evidence_engine import _candidate_atlas as operation_fn
        elif operation=="matches":
            from oss_adapters import _pdf_text_matches as operation_fn
        else:raise ValueError("Unknown PDF operation")
        result={"ok":True,"value":operation_fn(**request["kwargs"])}
        encoded=json.dumps(result,ensure_ascii=False,allow_nan=False).encode("utf-8")
        if len(encoded)>MAX_RESULT_BYTES:
            raise ResourceLimitError("PDF worker result limit exceeded")
    except Exception as exc:
        encoded=json.dumps({"ok":False,"error_type":type(exc).__name__,
                            "message":str(exc)[:500]},ensure_ascii=False).encode("utf-8")
    Path(result_path).write_bytes(encoded)

if __name__=="__main__":
    worker(sys.argv[1],sys.argv[2])
