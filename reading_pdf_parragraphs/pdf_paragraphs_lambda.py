# --- desactivar rutas que disparan FastAPI / proxy (igual a analyze_question.py) ---
import os
os.environ.setdefault("LITELLM_LOG", "ERROR")
os.environ.setdefault("LITELLM_CACHE", "False")
os.environ.setdefault("DSPY_LOGGING", "False")
# -----------------------------------------------------------------------------------

import json
import sys
import base64
from io import BytesIO
from typing import Any, Dict, List

# Para correr local con .env (en Lambda NO es necesario)
from dotenv import load_dotenv
load_dotenv()

# --- imports de tu pipeline ---
from pdf_reader.core import doc_summary, iter_pages_paragraphs
from ml.infer.classifier import load_model

# === Helpers ===
def _get_payload(event):
    # Invocación directa (CLI / Lambda Invoke)
    if isinstance(event, dict) and ("pdf_base64" in event or "s3_bucket" in event):
        return event

    # API Gateway HTTP API v2
    body = event.get("body") if isinstance(event, dict) else None
    if body is None:
        return {}

    if event.get("isBase64Encoded"):
        try:
            body = base64.b64decode(body).decode("utf-8", "ignore")
        except Exception:
            return {}

    try:
        return json.loads(body)
    except Exception:
        return {}
    
def _json_response(status: int, obj: Any) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(obj, ensure_ascii=False)
    }

def parse_pages_arg(spec: str, max_pages: int) -> set[int]:
    """
    Convierte '3-5,10,12-' en un set de páginas {3,4,5,10,12,13,...max_pages}.
    Acepta:
      - 'a-b' (ambos inclusive)
      - 'a-' (hasta max_pages)
      - '-b' (desde 1)
      - 'n'  (una sola página)
    Ignora elementos vacíos y recorta a [1, max_pages].
    """
    pages: set[int] = set()
    if not spec:
        return pages
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a) if a.strip() else 1
            end   = int(b) if b.strip() else max_pages
            start = max(1, start)
            end   = min(max_pages, end)
            if start <= end:
                pages.update(range(start, end + 1))
        else:
            try:
                n = int(part)
                if 1 <= n <= max_pages:
                    pages.add(n)
            except ValueError:
                pass
    return pages

def _save_tmp_pdf(pdf_bytes: bytes, filename: str = "incoming.pdf") -> str:
    """
    Guarda el PDF en /tmp (escritura permitida en Lambda) y devuelve la ruta.
    """
    tmp_path = f"/tmp/{filename}"
    with open(tmp_path, "wb") as f:
        f.write(pdf_bytes)
    return tmp_path

def _extract_body(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extrae un JSON desde:
      - event["body"] (string o ya dict)
      - o directamente el event si viene plano.
    Soporta API Gateway con isBase64Encoded.
    """
    if event is None:
        return {}
    # API Gateway v1/v2 puede mandar body string y flag base64
    body = event.get("body", event)
    if isinstance(body, str):
        if event.get("isBase64Encoded"):
            try:
                body = base64.b64decode(body).decode("utf-8")
            except Exception:
                # si falla, intentamos usarlo tal cual
                pass
        try:
            return json.loads(body)
        except Exception:
            # si no es JSON, devolvemos dict vacío
            return {}
    elif isinstance(body, dict):
        return body
    return {}

# === Core ===

def classify_pdf_from_bytes(pdf_bytes: bytes, pages_spec: str = "", y_gap: float = 15.0, indent_gap: float = 12.0) -> List[Dict[str, Any]]:
    """
    Recibe PDF en bytes, clasifica párrafos con tu pipeline y devuelve lista de dicts.
    """
    # Guardar a /tmp y usar el pipeline existente basado en ruta
    pdf_path = _save_tmp_pdf(pdf_bytes)

    model = load_model("ml/artifacts/v1")

    meta = doc_summary(pdf_path)
    total_pages = meta.get("pages") or 0
    pages_target = parse_pages_arg(pages_spec, total_pages) if pages_spec else set(range(1, total_pages + 1))

    results: List[Dict[str, Any]] = []
    for page in iter_pages_paragraphs(pdf_path, y_gap_threshold=y_gap, indent_threshold=indent_gap):
        if page["page_number"] not in pages_target:
            continue

        paras = page.get("paragraphs") or []
        if not paras:
            continue

        preds = model.classify_batch(paras)
        for p, pred in zip(paras, preds):
            results.append({
                "page": page["page_number"],
                "text": p.get("text", ""),
                # "left_x": p.get("left_x"),
                # "right_x": p.get("right_x"),
                # "start_y": p.get("start_y"),
                # "end_y": p.get("end_y"),
                # "lines_count": p.get("lines_count"),
                "label": pred["label"],
                "proba": pred["proba"],
            })

    return results

# === Lambda handler ===

def lambda_handler(event, context):
    data = _get_payload(event)
    """
    Espera un JSON con:
      - pdf_base64: str  (PDF en base64)  [recomendado ahora]
      - pages: str       (rango, ej. "2-5", "1,4,7-8", "10-", "-3")
      - y_gap: float     (umbral de salto vertical; default 15.0)
      - indent_gap: float(default 12.0)

    Devuelve:
      { paragraphs: [ {page, text, left_x, right_x, start_y, end_y, lines_count, label, proba}, ... ] }
    """
    try:
        body = _extract_body(event)

        # Parámetros
        pdf_b64 = body.get("pdf_base64")
        pages   = (body.get("pages") or "").strip()
        y_gap   = float(body.get("y_gap", 15.0))
        indent  = float(body.get("indent_gap", 12.0))

        if not pdf_b64:
            return _json_response(400, {"error": "Falta 'pdf_base64' en el body."})

        # Decode base64
        try:
            pdf_bytes = base64.b64decode(pdf_b64)
        except Exception as e:
            return _json_response(400, {"error": f"pdf_base64 inválido: {repr(e)}"})

        # Clasificar
        paragraphs = classify_pdf_from_bytes(pdf_bytes, pages_spec=pages, y_gap=y_gap, indent_gap=indent)
        return _json_response(200, {"paragraphs": paragraphs, "test": "este es mi test"})

    except Exception as e:
        # Log de emergencia y 500
        print("Exception:", repr(e), "python:", sys.version)
        return _json_response(500, {"error": str(e)})

# === Runner local ===
if __name__ == "__main__":
    # Para pruebas locales: lee events/event.json y ejecuta el handler
    try:
        with open("events/event.json", "r", encoding="utf-8") as f:
            evt = json.load(f)
    except FileNotFoundError:
        # fallback mínimo
        evt = {
            "body": json.dumps({
                "pdf_base64": "",   # pega aquí un base64 para probar
                "pages": "1-",
                "y_gap": 15.0,
                "indent_gap": 12.0
            }, ensure_ascii=False)
        }
    response = lambda_handler(evt, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))
