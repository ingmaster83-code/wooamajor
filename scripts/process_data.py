#!/usr/bin/env python3
"""
process_data.py - 원본 학과 데이터를 Jekyll 페이지 생성용 JSON으로 가공 (학교별 그룹화 + 시도별 분할)

입력: _rawdata/major_raw.json (fetch_major.py로 생성, 101,238건)
출력: _rawdata/schools_{도}.json x17 (시도별 분할, 학교 단위로 그룹화)
      search_index.json (검색용, 루트) — 학교명+학과명+지역

학교(SCHL_NM) 단위로 그룹화 — 대학원/캠퍼스가 별도 SCHL_NM으로 이미 분리돼 있어서
그대로 존중(예: "홍익대학교"와 "홍익대학교 영상·커뮤니케이션대학원"은 별도 페이지).
"기타(소속학과없음)" 등 무의미한 행은 제외.

사용법:
  python scripts/process_data.py [--limit N]
"""
import json, re, hashlib, sys, argparse
from pathlib import Path
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).parent.parent
RAW = ROOT / "_rawdata" / "major_raw.json"
RAWDATA_DIR = ROOT / "_rawdata"
SEARCH_INDEX_OUT = ROOT / "search_index.json"

DO_MAP = {
    "서울특별시": "서울", "부산광역시": "부산", "대구광역시": "대구",
    "인천광역시": "인천", "광주광역시": "광주", "대전광역시": "대전",
    "울산광역시": "울산", "세종특별자치시": "세종", "경기도": "경기",
    "강원특별자치도": "강원", "강원도": "강원",
    "충청북도": "충북", "충청남도": "충남",
    "전북특별자치도": "전북", "전라북도": "전북", "전라남도": "전남",
    "경상북도": "경북", "경상남도": "경남", "제주특별자치도": "제주", "제주도": "제주",
}


def guess_sido(raw, sggu):
    text = (raw or "").strip()
    sggu = (sggu or "").strip()
    if text == "전남광주통합특별시":
        return "광주" if sggu.endswith("구") else "전남"
    if text in DO_MAP:
        return DO_MAP[text]
    if text in DO_MAP.values():
        return text
    return ""


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w가-힣\s-]", "", text).strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    h = hashlib.md5(text.encode("utf-8")).hexdigest()[:6]
    return f"{slug}-{h}" if slug else h


def split_multi(s):
    """+ 로 이어붙은 다중값 필드를 리스트로 분리"""
    if not s:
        return []
    return [p.strip() for p in s.split("+") if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if args.limit:
        raw = raw[:args.limit]
        print(f"[--limit] 상위 {len(raw)}개만 처리")

    # 학교 단위로 그룹화
    by_school = defaultdict(list)
    skipped = 0
    for d in raw:
        school = (d.get("SCHL_NM") or "").strip()
        major = (d.get("SCSBJT_NM") or "").strip()
        if not school or not major or major.startswith("기타(소속"):
            skipped += 1
            continue
        by_school[school].append(d)

    print(f"학교 수: {len(by_school)}개 (제외: {skipped}건)")

    schools = []
    seen_slugs = Counter()
    for school, rows in by_school.items():
        first = rows[0]
        do_short = guess_sido(first.get("CTPV_NM"), first.get("SGG_NM"))
        sigungu = (first.get("SGG_NM") or "").strip()
        if sigungu == "없음":  # 세종시 일부 레코드는 시군구가 명시적으로 "없음"으로 옴(세종은 단일 행정구역)
            sigungu = "기타"
        if not do_short or not sigungu:
            continue

        slug = slugify(school)
        seen_slugs[slug] += 1
        if seen_slugs[slug] > 1:
            slug = f"{slug}-{seen_slugs[slug]}"

        majors = []
        for r in rows:
            majors.append({
                "name": (r.get("SCSBJT_NM") or "").strip(),
                "degree": (r.get("DEG_CRSE_CRS_NM") or "").strip(),
                "dayNight": (r.get("DAN_CRS_NM") or "").strip(),
                "affil": (r.get("UNIV_ONESLF_AFIL_NM") or "").strip(),
                "college": (r.get("COLLEGE_NM") or "").strip(),
                "term": (r.get("LSSN_TERM") or "").strip(),
                "capacity": (r.get("MTCLTN_FXNO_CNT") or "").strip(),
                "graduates": (r.get("GRA_CNT") or "").strip(),
                "careers": split_multi(r.get("RELAT_CR_NM")),
            })

        schoolType = (first.get("SCHL_SE_NM") or "").strip()
        affils = sorted(set(m["affil"] for m in majors if m["affil"]))
        degrees = sorted(set(m["degree"] for m in majors if m["degree"]))

        schools.append({
            "schoolName": school,
            "slug": slug,
            "doShort": do_short,
            "sigungu": sigungu,
            "schoolType": schoolType,
            "majorCount": len(majors),
            "affils": affils,
            "degrees": degrees,
            "majors": majors,
        })

    by_do = defaultdict(list)
    for s in schools:
        by_do[s["doShort"]].append(s)

    RAWDATA_DIR.mkdir(parents=True, exist_ok=True)
    for do, group in by_do.items():
        out = RAWDATA_DIR / f"schools_{do}.json"
        out.write_text(json.dumps(group, ensure_ascii=False), encoding="utf-8")
        size_mb = out.stat().st_size / 1024 / 1024
        print(f"  {do}: {len(group)}개교 → {out.name} ({size_mb:.1f}MB)")

    print(f"\n총 {len(schools)}개교 저장 (시도 {len(by_do)}개 파일)")

    do_counts = Counter(s["doShort"] for s in schools)
    print("\n지역별 학교 수:")
    for do, cnt in sorted(do_counts.items(), key=lambda x: -x[1]):
        print(f"  {do}: {cnt}개교")

    total_majors = sum(s["majorCount"] for s in schools)
    print(f"\n총 학과/과정 수: {total_majors}건")

    # 검색 인덱스: 학교 단위(가벼움) + 학과명 일부 텍스트 포함(검색 매칭용)
    index = [
        {
            "n": s["schoolName"], "do": s["doShort"], "sg": s["sigungu"],
            "s": s["slug"], "mc": s["majorCount"],
            "mn": "|".join(sorted(set(m["name"] for m in s["majors"])))[:500],
        }
        for s in schools
    ]
    SEARCH_INDEX_OUT.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    size_mb = SEARCH_INDEX_OUT.stat().st_size / 1024 / 1024
    print(f"\n검색 인덱스 {len(index)}개교 저장 → {SEARCH_INDEX_OUT} ({size_mb:.1f}MB)")


if __name__ == "__main__":
    main()
