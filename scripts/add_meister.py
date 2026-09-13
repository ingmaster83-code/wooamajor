# -*- coding: utf-8 -*-
"""전국초중등학교위치표준데이터(data.go.kr id 15021148)에서 마이스터고만 추려서
기존 schools_{도}.json 샤드에 kind='meister' 레코드로 병합.

원본: _rawdata_school/school_page1.json + school_page2.json (전국 초중고 12,011개)
"""
import json
import re
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "_rawdata_school"
SCHOOLS_DIR = ROOT / "_rawdata"

SIDO_MAP = {
    "서울특별시교육청": "서울", "부산광역시교육청": "부산", "대구광역시교육청": "대구",
    "인천광역시교육청": "인천", "광주광역시교육청": "광주", "대전광역시교육청": "대전",
    "울산광역시교육청": "울산", "세종특별자치시교육청": "세종", "경기도교육청": "경기",
    "강원특별자치도교육청": "강원", "충청북도교육청": "충북", "충청남도교육청": "충남",
    "전북특별자치도교육청": "전북", "전라남도교육청": "전남", "경상북도교육청": "경북",
    "경상남도교육청": "경남", "제주특별자치도교육청": "제주",
}


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w가-힣\s-]", "", text).strip()
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    h = hashlib.md5(text.encode("utf-8")).hexdigest()[:6]
    return f"{slug}-{h}" if slug else h


def extract_sigungu(addr: str) -> str:
    parts = addr.split()
    if len(parts) < 2:
        return ""
    # "광주광역시 광산구 ..." -> 광산구 / "경기도 안성시 ..." -> 안성시
    return parts[1]


def main():
    rows = []
    for p in [1, 2]:
        rows.extend(json.loads((RAW_DIR / f"school_page{p}.json").read_text(encoding="utf-8")))

    # 마이스터고로 지정됐지만 교명에 "마이스터고"가 없는 경우(개편 전 교명 유지) 수동 추가
    LEGACY_NAME_MEISTERS = {"충북반도체고등학교", "인천반도체고등학교"}

    meister = [
        r for r in rows
        if r.get("OPER_STTUS") == "운영"
        and ("마이스터고" in r.get("SCHOOL_NM", "") or r.get("SCHOOL_NM", "") in LEGACY_NAME_MEISTERS)
    ]
    print(f"마이스터고 {len(meister)}개 발견")

    by_do = {}
    for r in meister:
        do_short = SIDO_MAP.get(r.get("CDDC_NM", ""), "")
        if not do_short:
            print(f"  ! 시도 매핑 실패: {r.get('CDDC_NM')} ({r.get('SCHOOL_NM')})")
            continue
        addr = r.get("RDNMADR") or r.get("LNMADR") or ""
        rec = {
            "schoolName": r["SCHOOL_NM"],
            "slug": slugify(r["SCHOOL_NM"]),
            "doShort": do_short,
            "sigungu": extract_sigungu(addr),
            "schoolType": "마이스터고",
            "kind": "meister",
            "majorCount": 0,
            "affils": [],
            "degrees": [],
            "majors": [],
            "address": addr,
            "foundDate": r.get("FOND_DATE", ""),
            "foundType": r.get("FOND_TYPE", ""),
            "eduOffice": r.get("EDC_SPORT_NM", ""),
            "lat": r.get("LATITUDE", ""),
            "lng": r.get("LONGITUDE", ""),
        }
        by_do.setdefault(do_short, []).append(rec)

    total_added = 0
    for do_short, recs in by_do.items():
        shard_path = SCHOOLS_DIR / f"schools_{do_short}.json"
        existing = json.loads(shard_path.read_text(encoding="utf-8")) if shard_path.exists() else []
        existing_names = {s["schoolName"] for s in existing}
        new_recs = [r for r in recs if r["schoolName"] not in existing_names]
        existing.extend(new_recs)
        shard_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        total_added += len(new_recs)
        print(f"  {do_short}: +{len(new_recs)} (skip {len(recs) - len(new_recs)} dup)")

    print(f"총 {total_added}개 마이스터고 병합 완료")


if __name__ == "__main__":
    main()
