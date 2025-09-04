import argparse
from email import parser
import json
from pdf_reader.core import doc_summary, first_page_text, iter_pages_lines, iter_pages_paragraphs
from ml.infer.classifier import load_model

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

def main():
    parser = argparse.ArgumentParser(description="Lector PDF - Fase inicial")
    parser.add_argument("pdf", help="Ruta al archivo PDF de entrada")
    parser.add_argument("--show-lines", action="store_true",
                        help="Muestra las primeras 10 líneas detectadas de la página 1")
    parser.add_argument("--show-paragraphs", action="store_true",
                        help="Muestra los primeros 5 párrafos detectados en la página 1")
    parser.add_argument("--y-gap", type=float, default=15.0, help="Umbral de salto vertical para párrafos")
    parser.add_argument("--indent-gap", type=float, default=12.0, help="Umbral de indentación para párrafos")
    parser.add_argument("--page", type=int, default=1,
                    help="Número de página a mostrar (1-based)")
    parser.add_argument("--classify", action="store_true",
                    help="Clasifica los párrafos")
    parser.add_argument("--list_all_paragraphs", action="store_true",
                    help="Lista todos los párrafos del documento")
    parser.add_argument("--pages", type=str, default="",
                    help="Rango de páginas a procesar (1-based). Ej: '3-5', '10-', '-4', '1,4,7-9', '-'")
    parser.add_argument("--export-json", type=str, default="",
                    help="Ruta del JSON de salida con todos los párrafos clasificados")

    args = parser.parse_args()

    print("== Resumen ==")
    print(doc_summary(args.pdf))

    print("\n== Primeros 300 caracteres ==")
    print(first_page_text(args.pdf))

    if args.show_lines:
        print(f"\n== Primeras 10 líneas (página {args.page}) ==")
        for page in iter_pages_lines(args.pdf):
            if page["page_number"] == args.page:
                for i, L in enumerate(page["lines"], start=1):
                    if i > 10:
                        break
                    print(f"[y={L['origin_y']:.1f} x={L['origin_x']:.1f}] {L['text'][:120]}")
                break
    
    if args.show_paragraphs:
       
        print(f"\n== Primeros 5 párrafos (página {args.page}) ==")
        for page in iter_pages_paragraphs(
            args.pdf, y_gap_threshold=args.y_gap, indent_threshold=args.indent_gap
        ):
            if page["page_number"] == args.page:
                for i, p in enumerate(page["paragraphs"], start=1):
                    if i > 5:
                        break
                    snippet = p["text"][:400].replace("\n", " ")
                    print(f"[lines={p['lines_count']} y0={p['start_y']:.1f} x0={p['left_x']:.1f} x1={p['right_x']:.1f}] {snippet}")
                break
            
    if args.classify:

        model = load_model("ml/artifacts/v1")

        target_page_paras = []
        for page in iter_pages_paragraphs(
            args.pdf, y_gap_threshold=args.y_gap, indent_threshold=args.indent_gap
        ):
            if page["page_number"] == args.page:
                target_page_paras = page["paragraphs"]
                break

        print(f"\n== Clasificación (página {args.page}) ==")
        if not target_page_paras:
            print("(no hay párrafos en esta página)")
        else:
            preds = model.classify_batch(target_page_paras)
            for p, pred in zip(target_page_paras[:10], preds[:10]):  # primeras 10
                snippet = p["text"].replace("\n", " ")[:120]
                orig_x = p.get("origin_x", p.get("left_x"))
                print(f"{pred['label']:14s} p={pred['proba']:.2f}  x={orig_x:.1f} | {snippet}")

    if args.list_all_paragraphs:
        model = load_model("ml/artifacts/v1")  # carga etiquetas y stub
        total = 0
        for page in iter_pages_paragraphs(
            args.pdf,
            y_gap_threshold=args.y_gap,
            indent_threshold=args.indent_gap,
        ):
            paras = page.get("paragraphs") or []
            if not paras:
                continue

            # Clasificar en batch toda la página
            preds = model.classify_batch(paras)

            for p, pred in zip(paras, preds):
                text = (p.get("text") or "").replace("\n", " ").strip()
                if len(text) > 200:
                    text = text[:200].rstrip() + "…"

                x = p.get("origin_x", p.get("left_x"))
                try:
                    x_fmt = f"{float(x):.1f}" if x is not None else "-"
                except Exception:
                    x_fmt = "-"

                print(
                    f"P{page['page_number']:>3} | x={x_fmt} | {pred['label']:<12s} p={pred['proba']:.2f} | {text}"
                ) 
                total += 1

        print(f"\nTotal de párrafos: {total}")

    if args.classify:
        model = load_model("ml/artifacts/v1")
        target_page_paras = []
        for page in iter_pages_paragraphs(
            args.pdf, y_gap_threshold=args.y_gap, indent_threshold=args.indent_gap
        ):
            if page["page_number"] == args.page:
                target_page_paras = page["paragraphs"]
                break

        print(f"\n== Clasificación (página {args.page}) ==")
        if not target_page_paras:
            print("(no hay párrafos en esta página)")
        else:
            preds = model.classify_batch(target_page_paras)
            for p, pred in zip(target_page_paras[:10], preds[:10]):  # primeras 10
                snippet = p["text"].replace("\n", " ")[:120]
                orig_x = p.get("left_x", p.get("origin_x"))
                print(f"{pred['label']:14s} p={pred['proba']:.2f}  x={orig_x:.1f} | {snippet}")

    if args.list_all_paragraphs:
        model = load_model("ml/artifacts/v1")  # carga etiquetas y stub
        total = 0
        for page in iter_pages_paragraphs(
            args.pdf,
            y_gap_threshold=args.y_gap,
            indent_threshold=args.indent_gap,
        ):
            paras = page.get("paragraphs") or []
            if not paras:
                continue

            # Clasificar en batch toda la página
            preds = model.classify_batch(paras)

            for p, pred in zip(paras, preds):
                text = (p.get("text") or "").replace("\n", " ").strip()
                if len(text) > 200:
                    text = text[:200].rstrip() + "…"

                x = p.get("left_x", p.get("origin_x"))
                try:
                    x_fmt = f"{float(x):.1f}" if x is not None else "-"
                except Exception:
                    x_fmt = "-"

                print(
                    f"P{page['page_number']:>3} | x={x_fmt} | {pred['label']:<12s} p={pred['proba']:.2f} | {text}"
                )
                total += 1

        print(f"\nTotal de párrafos: {total}")
    
    if args.export_json:
        model = load_model("ml/artifacts/v1")

        total_pages = doc_summary(args.pdf)["pages"] or 0
        # Si --pages viene vacío, usamos la página única de --page
        pages_target = parse_pages_arg(args.pages, total_pages)
        if not pages_target:
            pages_target = {args.page}

        results = []
        for page in iter_pages_paragraphs(
            args.pdf,
            y_gap_threshold=args.y_gap,
            indent_threshold=args.indent_gap,
        ):
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
                    "left_x": p.get("left_x"),
                    "right_x": p.get("right_x"),
                    "start_y": p.get("start_y"),
                    "end_y": p.get("end_y"),
                    "lines_count": p.get("lines_count"),
                    "label": pred["label"],
                    "proba": pred["proba"],
                })

        with open(args.export_json, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\nGuardado {len(results)} párrafos en: {args.export_json}")
    

if __name__ == "__main__":
    main()