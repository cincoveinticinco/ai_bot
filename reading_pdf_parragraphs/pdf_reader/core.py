import fitz  # PyMuPDF
import math
from typing import Iterator, Dict, Any, List, Optional
import re

_SOFT_HYPHEN = "\u00AD"  # soft hyphen (invisible)

# Une "Casca- \n das" -> "Cascadas" (si la siguiente empieza en minúscula, ES/PT)
_HYPHEN_JOIN_RE = re.compile(
    r"(\w)(?:-\s+|\u00AD\s*)([a-záéíóúñçãõâêôàüïöëä0-9])"
)

_INVISIBLES_RE = re.compile(r"[\u200B-\u200D\uFEFF]")  # zero-width & BOM


def open_pdf(pdf_path: str) -> fitz.Document:
    """Abre un PDF y retorna el objeto Document de PyMuPDF."""
    return fitz.open(pdf_path)

def doc_summary(pdf_path: str) -> dict:
    """Devuelve páginas y metadatos básicos."""
    with open_pdf(pdf_path) as doc:
        meta = doc.metadata or {}
        return {
            "pages": doc.page_count,
            "title": meta.get("title"),
            "author": meta.get("author"),
        }

def first_page_text(pdf_path: str, n_chars: int = 300) -> str:
    """Devuelve los primeros n_chars de la primera página."""
    with open_pdf(pdf_path) as doc:
        if doc.page_count == 0:
            return ""
        text = doc[0].get_text("text")
        return text[:n_chars].replace("\n", " ")

def iter_pages_lines(pdf_path: str) -> Iterator[Dict[str, Any]]:
    print("=====ACA EXTRAE EL TEXTO DE CADA PÁGINA======")
    """
    Devuelve por página una lista de 'líneas' ordenadas.
    Cada línea: {text, origin_x, origin_y, end_x, size, font, bbox}
    """
    with open_pdf(pdf_path) as doc:
        for i, page in enumerate(doc, start=1):
            data = page.get_text("dict")
            page_height = float(page.rect.height)
            lines: List[Dict[str, Any]] = []
            for block in data.get("blocks", []):
                if block.get("type") != 0:  # solo texto
                    continue
                for line in block.get("lines", []):
                    # print("LINEA DETECTADA:", line)  # Debug line
                    spans = line.get("spans") or []
                    if not spans:
                        continue
                    # Filtrar marcas de agua / texto en diagonal
                    # Usamos la dirección del primer span como referencia
                    if not _is_horizontal_dir(line.get('dir')):
                         continue
                    
                    text = "".join(s.get("text", "") for s in spans)
                    text = _clean_line_text(text)  # limpia NBSP, invisibles, soft hyphen, espacios
                    
                    bbox = line.get("bbox") or spans[0].get("bbox")
                    origin_x, origin_y, end_x, end_y = bbox[0], bbox[1], bbox[2], bbox[3]
                   
                    if not text or float(origin_y) < 50 or float(origin_y) > (page_height - 50):
                        # if text:
                        #     print("--" * 50)
                        #     print("Skipping line due to position or empty text")  # Debug line
                        #     print(text)
                        #     print("--" * 50)
                        continue
                    s0 = spans[0]
                    lines.append({
                        "text": text,
                        "origin_x": float(origin_x),
                        "origin_y": float(origin_y),
                        "end_x": float(end_x),
                        "end_y": float(end_y),
                        "size": float(s0.get("size", 0)),
                        "font": s0.get("font", ""),
                        "flags": s0.get("flags", 0),
                        "bbox": bbox,
                    })

            # Ordenar por y luego x
            lines.sort(key=lambda L: (round(L["origin_y"], 1), L["origin_x"]))

            # 🔹 Eliminar duplicados de texto en la misma línea (misma y redondeada)
            seen = set()
            filtered = []
            for L in lines:
                key = (round(L["origin_y"], 1), L["text"])
                if key in seen:
                    continue  # duplicado → lo saltamos
                seen.add(key)
                filtered.append(L)

            yield {"page_number": i, "lines": filtered}

def group_lines_to_paragraphs(
    lines: List[Dict[str, Any]],
    y_gap_threshold: float = 15.0,
    indent_threshold: float = 12.0,
) -> List[Dict[str, Any]]:
    """
    Agrupa líneas contiguas en párrafos usando una heurística:
    - Nuevo párrafo si el salto vertical (Δy) entre líneas supera y_gap_threshold
      o si hay cambio de indentación notable (origin_x diferencia > indent_threshold)
      o si la línea previa termina con punto y la siguiente está claramente separada.
    Retorna: lista de {text, start_y, end_y, left_x, right_x, lines_count}
    """
    paragraphs: List[Dict[str, Any]] = []
    if not lines:
        return paragraphs

    def new_para_from_line(L):
        return {
            "text": L["text"],
            "start_y": L["origin_y"],
            "end_y": L["origin_y"],
            "left_x": L["origin_x"],
            "right_x": L["end_x"],
            "lines_count": 1,
        }
    
    def _is_bold(font: str) -> bool:
        """
        Detecta heurísticamente si el nombre de la fuente indica estilo negrita.
        Busca tokens comunes en el nombre de la fuente (bold, black, demi, bd, bf, blk).
        """
        if not font:
            return False
        fname = font.lower()
        return bool(re.search(r"\b(bold|black|demi|bd|bf|blk)\b", fname))

    cur = new_para_from_line(lines[0])
    prev = lines[0]

    for L in lines[1:]:
        dy = L["origin_y"] - prev["origin_y"]
        d_indent = abs(L["origin_x"] - prev["origin_x"])
        prev_ends_sentence = prev["text"].rstrip().endswith((".", "!", "?"))
        
        change_line_style = _is_bold(L["font"]) != _is_bold(prev["font"])

        should_break = False
        if dy > y_gap_threshold:
            should_break = True
        elif d_indent > indent_threshold and dy > (y_gap_threshold * 0.5):
            should_break = True
        elif prev_ends_sentence and dy > (y_gap_threshold * 0.8):
            should_break = True
        elif change_line_style:
            should_break = True
        elif L["flags"] != prev["flags"]:
            should_break = True

        if should_break:
            paragraphs.append(cur)
            cur = new_para_from_line(L)
        else:
            # Continuación del párrafo actual
            # Unir línea al párrafo actual con normalización de guiones
            merged = (cur["text"].rstrip() + " " + L["text"].lstrip()).strip()
            merged = normalize_hyphens(merged)
            cur["text"] = merged
            cur["end_y"] = L["origin_y"]
            cur["left_x"] = min(cur["left_x"], L["origin_x"])
            cur["right_x"] = max(cur["right_x"], L["end_x"])
            cur["lines_count"] += 1

        prev = L

    paragraphs.append(cur)
    return paragraphs

def iter_pages_paragraphs(
    pdf_path: str,
    y_gap_threshold: float = 15.0,   # antes 6.0
    indent_threshold: float = 12.0,
) -> Iterator[Dict[str, Any]]:
    """Devuelve párrafos por página aplicando la heurística anterior."""
    for page in iter_pages_lines(pdf_path):
        paras = group_lines_to_paragraphs(
            page["lines"],
            y_gap_threshold=y_gap_threshold,
            indent_threshold=indent_threshold,
        )
        yield {"page_number": page["page_number"], "paragraphs": paras}

def normalize_hyphens(text: str) -> str:
    """
    Normaliza guiones de corte de línea:
    - Une palabras divididas por guion al final de línea cuando la siguiente línea
      comienza con minúscula (Casca- [nl] das -> Cascadas).
    - Elimina soft hyphen.
    - Mantiene guiones legítimos (no une si la siguiente empieza en Mayúscula).
    """
    if not text:
        return text
    # quitar soft hyphen suelto
    text = text.replace(_SOFT_HYPHEN, "")
    # unir palabra-cortada + minúscula
    text = _HYPHEN_JOIN_RE.sub(r"\1\2", text)
    return text

def _clean_line_text(t: str) -> str:
    """
    Limpieza ligera de cada línea:
    - Normaliza NBSP (\xa0) y thin NBSP (\u202f) a espacio.
    - Elimina zero-width (\u200B-\u200D, \uFEFF).
    - Elimina soft hyphen.
    - Quita asteriscos decorativos finales.
    - Colapsa espacios múltiples.
    """
    if not t:
        return t
    # Normalizaciones de espacios e invisibles
    t = t.replace("\xa0", " ").replace("\u202f", " ")
    t = _INVISIBLES_RE.sub("", t)
    # Soft hyphen
    t = t.replace(_SOFT_HYPHEN, "")
    # Asteriscos decorativos al final (p. ej., "TÍTULO*")
    t = re.sub(r"\*+$", "", t)
    # Colapsar espacios
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _is_horizontal_dir(direction: Optional[tuple], tol_deg: float = 2.0) -> bool:
    """
    Devuelve True si el vector de dirección (dx, dy) indica texto horizontal.
    Considera horizontales los ángulos cercanos a 0° o 180° dentro de una tolerancia.
    """
    if not direction:
        return True  # si no hay info, asumimos horizontal
    dx, dy = direction
    angle = math.degrees(math.atan2(dy, dx))  # [-180, 180]
    # normalizamos a [0, 180)
    angle = abs(angle) % 180.0
    # cerca de 0° o de 180° (que equivale a 0°)
    return (angle <= tol_deg) or (abs(180.0 - angle) <= tol_deg)
