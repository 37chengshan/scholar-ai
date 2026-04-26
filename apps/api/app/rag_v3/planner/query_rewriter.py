from __future__ import annotations


def rewrite_query(query: str, query_family: str) -> list[str]:
    base = str(query or "").strip()
    family = str(query_family or "fact").strip().lower()
    if not base:
        return []

    variants = [base]
    if family in {"table", "figure", "numeric"}:
        variants.append(f"{base} results table figure caption")
    elif family in {"compare", "cross_paper", "survey"}:
        variants.append(f"{base} across papers comparison")
    elif family == "method":
        variants.append(f"{base} method architecture approach")
    else:
        variants.append(f"{base} key evidence")
    return variants
