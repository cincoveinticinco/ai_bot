import json
import os
import re
from typing import List, Dict, Any, Tuple

# Heurísticas básicas (solo para probar el flujo)
_X_TOL = 14.0

_TARGET_X = {
    "Action": 108.0,
    "General": 108.0,
    "Shot": 108.0,
    "Character": 252.0,
    "Parenthetical": 208.0,
    "Dialogue": 180.0,
    # "Scene Heading": depende del texto → 55 si empieza con número, 108 si no
    # "Transition": usa umbral (>= 370–399)
}
# ===== Cues de texto simples (ayudan cuando comparten el mismo X) =====
_RE_SCENE_FLEX = re.compile(
    r"^\s*(\d+[A-Z]?\.?\s*)?"                # número de escena opcional (1, 12A, 3.)
    r"(?:INT|EXT|INT/EXT|EXT/INT|I/E|E/I)"   # variantes
    r"\.?\b",                                # punto opcional
    re.IGNORECASE
)

# Tokens de "tiempo del día" (ES + EN) para casos sin INT/EXT:
_SCENE_TOD_TOKENS = (
    r"DIA|DÍA|"                    # es/pt
    r"NOCHE|NOITE|"
    r"TARDE|"
    r"MAÑANA|MANHA|MANHÃ|"        # morning
    r"MEDIODIA|MEDIODÍA|MEIO[- ]DIA|MEIO[- ]DÍA|"  # noon
    r"AMANECER|AMANHECER|ALBA|ALVOR|ALVORECER|"    # dawn
    r"ANOCHECER|ANOITECER|ENTARDECER|CREPUSCULO|CREPÚSCULO|"  # dusk/twilight
    r"PÔR[- ]DO[- ]SOL|POR[- ]DO[- ]SOL|NASCER[- ]DO[- ]SOL|" # sunset/sunrise (pt)
    r"NOITINHA|TARDEZINHA|"        # late evening / late afternoon (pt coloquial)
    r"DAY|NIGHT|MORNING|AFTERNOON|EVENING|DAWN|DUSK|SUNRISE|SUNSET|LATER|"
    r"CONTINUO|CONTÍNUO|CONTINUA(?:ÇÃO)?|CONTINUOUS|CONT\.|CONT"  # continuo/continua/cont.
)
_RE_SCENE_DASH_TOD = re.compile(
    rf"\s[-—]\s.*\b(?:{_SCENE_TOD_TOKENS})\b",  # ‘LUGAR - DÍA’, ‘… — NOCHE’, etc.
    re.IGNORECASE
)
_RE_TRANS = re.compile(
    r"(CUT TO:|DISSOLVE TO:|FADE (IN|OUT):|SMASH CUT TO:|MATCH CUT TO:"        # inglés
    r"|CORTE A:|FUNDIDO A:|FUNDIDO (ENTRADA|SALIDA):|CORTE BRUSCO A:|INTERCORTE A:|CORTE POR COINCIDENCIA A:"  # español
    r"|CORTE PARA:|DISSOLVE PARA:|FUSÃO (ENTRADA|SAÍDA):|CORTE SECO PARA:|CORTE POR COINCIDÊNCIA PARA:)"      # portugués
    r"\s*$",
    re.IGNORECASE
)
_RE_SHOT  = re.compile(r"^(CLOSE ON|ANGLE ON|POV|INSERT|SHOT|WIDE SHOT|ECU|CU|MS|WS)\b", re.IGNORECASE)
_RE_PAREN = re.compile(r"^\s*\(.*\)\s*$")

_CENTER_X = 306.0
_CENTER_TOL = 16.0  # margen en puntos

# --- utilidades ---
def _get_x(p: Dict[str, Any]) -> float:
    x = p.get("left_x", p.get("origin_x"))
    try:
        return float(x) if x is not None else 0.0
    except Exception:
        return 0.0

def _close_to(x: float, target: float, tol: float = _X_TOL) -> bool:
    return abs(x - target) <= tol

def _load_labels(model_dir: str) -> List[str]:
    labels_path = os.path.join(model_dir, "labels.json")
    if not os.path.exists(labels_path):
        return ["Other"]   # ← coherente con el resto del código
    with open(labels_path, "r", encoding="utf-8") as f:
        return json.load(f)

def _strip_name_prefix(t: str) -> str:
    """
    Devuelve el 'nombre' antes de cualquier paréntesis o dos puntos.
    Ej.: 'MAGO (CONT’D)' -> 'MAGO' ;  'ANGIE (AL TELÉFONO):' -> 'ANGIE'
    """
    base = t.split('(')[0]
    base = base.split(':')[0]
    return base.strip()

def _is_character_line(t: str, x: float) -> bool:
    """
    Heurística robusta para 'Character':
    - X ≈ 252 (± tolerancia)
    - El token antes del primer paréntesis/':' está en MAYÚSCULAS (con acentos)
    - Sin límite de longitud total (puede llevar paréntesis largos)
    """
    if not _close_to(x, _TARGET_X["Character"]):
        return False
    name = _strip_name_prefix(t)
    if not name or len(name) > 50:   # nombres raramente > 50
        return False
    # Debe ser mayúsculas (permitimos dígitos, espacios, guiones, apóstrofos)
    return _looks_all_caps(name)

def _looks_all_caps(s: str) -> bool:
    """
    Devuelve True si la parte 'alfabética' del string está en mayúsculas.
    Soporta acentos Unicode (ES/PT), p.ej. JOÃO, ÂNGELA, MÃE, CÉU, SALOMÉ, etc.
    Ignora dígitos, espacios y puntuación comunes ((),.-’'`´/).
    """
    core = get_alpha_core(s)
    if not core:          # no hay letras (solo símbolos/espacios)
        return False
    return core == core.upper()


def get_alpha_core(s):
    core = re.sub(r"[0-9 .,?¿!¡'\"()\/\-’`´]+", "", s, flags=re.UNICODE).strip()
    return core

def _bbox_x0x1(p: Dict[str, Any]) -> Tuple[float, float]:
    # Caso típico en tus párrafos
    if "left_x" in p and "right_x" in p:
        try:
            return float(p["left_x"] or 0.0), float(p["right_x"] or 0.0)
        except Exception:
            return 0.0, 0.0
    # Alternativas
    x0 = p.get("origin_x")
    x1 = p.get("end_x")
    if x0 is not None and x1 is not None:
        return float(x0), float(x1)
    bbox = p.get("bbox")
    if bbox and len(bbox) >= 3:
        return float(bbox[0]), float(bbox[2])
    # Último recurso
    x0 = p.get("left_x") or 0.0
    x1 = p.get("right_x") or x0
    return float(x0), float(x1)


def _is_centered(p, mid_target: float = _CENTER_X, tol: float = _CENTER_TOL) -> bool:
    """
    Considera centrado si el punto medio horizontal del párrafo
    (left_x + right_x)/2 cae cerca de mid_target (p. ej. 306 ± tol).
    """
    x0, x1 = _bbox_x0x1(p)  # usa tus left_x / right_x
    mid_text = (x0 + x1) / 2.0
    return abs(mid_text - mid_target) <= tol

class DummyHeuristicClassifier:
    def __init__(self, labels: List[str]):
        self.labels = labels
        self.index = {name: i for i, name in enumerate(labels)}

    def _pick(self, name: str, proba: float) -> Tuple[int, float]:
        idx = self.index.get(name, self.index.get("OTRO", 0))
        return idx, proba

    def classify_batch(self, paras: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for p in paras:
            t = (p.get("text") or "").strip()
            x = _get_x(p)

            # 1) TRANSITION: a la derecha + patrón típico
            if x >= 370.0 or _RE_TRANS.search(t):
                label = "Transition"
                proba = 0.9 if x >= 370.0 else 0.8
            # 2) SCENE HEADING: INT./EXT. ; si empieza con número → x≈55, sino x≈108
            # 2) SCENE HEADING (flexible):
            #    a) si matchea INT/EXT flexible con número opcional
            #    b) o si trae ' - ' / ' — ' y un token de tiempo del día
            #    c) y además respeta la X típica: ~55 si empieza con número, ~108 si no
            elif _RE_SCENE_FLEX.match(t) or _RE_SCENE_DASH_TOD.search(t) or re.search(r"\bOMITTED\b", t, re.IGNORECASE):
                starts_with_num = bool(re.match(r"^\s*\d+[A-Z]?\.?", t))
                target = 55.0 if starts_with_num else 108.0
                if _close_to(x, target):
                    label, proba = "Scene Heading", 0.9
                else:
                    # Acepta como heading pero con menor confianza si la X se fue un poco
                    label, proba = "Scene Heading", 0.75
           # 3) CHARACTER: centrado ~252; nombre en mayúsculas (el resto puede llevar paréntesis/CONT’D)
            elif _is_character_line(t, x):
                label, proba = "Character", 0.92
            # 4) PARENTHETICAL: línea entre paréntesis en ~208
            elif _RE_PAREN.match(t) and _close_to(x, _TARGET_X["Parenthetical"]):
                label, proba = "Parenthetical", 0.9
            # 5) DIALOGUE: bloque a ~180 (no todo caps)
            elif _close_to(x, _TARGET_X["Dialogue"]):
                label, proba = "Dialogue", 0.8
            # 6) SHOT: palabras clave de plano a ~108
            elif _RE_SHOT.match(t) and _close_to(x, _TARGET_X["Shot"]):
                label, proba = "Shot", 0.8
            # 7) ACTION/GENERAL: ambos a ~108 → decide por texto (allcaps corto=título → General)
            # se eliminan por ahor alos generales
            elif _close_to(x, _TARGET_X["Action"]):
                if len(t) < 30 and not _looks_all_caps(t):
                    if t.endswith(":"):
                        label, proba = "Transition", 0.8
                    else:
                        label, proba = "Action", 0.7
                else:
                    label, proba = "Action", 0.7

            # 8) End of Act — SOLO si nada anterior aplicó
            elif _is_centered(p) and _looks_all_caps(t):
                label, proba = "End of Act", 0.88
            # 9) NUMBER: entero, decimal, o entero + letra (p.ej. 3A)
            elif (
                re.fullmatch(
                    r"\d+",
                    (t_num := re.sub(r"[\s\u00a0\u200b\u200c\u200d\ufeff]+", "", t)),
                )                               # 123 (incluye espacios/NBSP/ZWSP invisibles)
                or re.fullmatch(r"\d+\.\d+", t_num)          # 12.34
                or re.fullmatch(r"\d+[A-Za-z]", t_num)       # 3A, 12B
            ):
                label, proba = "Number", 0.9
            else:
                label, proba = "Other", 0.5

            idx = self.index.get(label, self.index.get("Other", 0))
            out.append({"label_id": idx, "label": self.labels[idx], "proba": proba, "origin_x": x})
        # Check if current label is 'Character' and next is not 'Parenthetical' or 'Dialogue'
        for i, o in enumerate(out):
            if o['label'] == 'Character':
                if i + 1 < len(out) and out[i + 1]['label'] not in ['Parenthetical', 'Dialogue']:
                    o['label'] = 'Other'
                    o['proba'] = 0.88
        return out


def load_model(model_dir: str):
    labels = _load_labels(model_dir)
    return DummyHeuristicClassifier(labels)