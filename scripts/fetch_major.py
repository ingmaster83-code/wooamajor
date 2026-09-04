"""
fetch_major.py — 전국대학별학과정보표준데이터 다운로드
data.go.kr download/standard.json 직접 다운로드 (API 키 불필요)

publicDataPk=15107737, svcTableNm=tn_pubr_public_univ_major_svc
확인된 규모: 101,238건 (2025년 데이터만, 과거 연도 없음), 학교 수 1,990개교
제공기관: 한국대학교육협의회 (단일 출처, 지자체 파편화 아님)
2026-09-04 확인.
"""
import json
import time
from pathlib import Path
import requests

BASE = "https://www.data.go.kr/download/standard.json"
PUBLIC_DATA_PK = "15107737"
SVC_TABLE = "tn_pubr_public_univ_major_svc"

COLUMNS = [
    "YR", "CTPV_CD", "CTPV_NM", "SGG_CD", "SGG_NM",
    "SCHL_NM", "SCHL_SE_NM", "LSSN_TERM", "DEG_CRSE_CRS_NM", "DAN_CRS_NM",
    "SCSBJT_STTS_NM", "SCSBJT_NM", "SCSBJT_CD_NM", "STD_CLSF_AFIL_CD",
    "UNIV_ONESLF_AFIL_NM", "COLLEGE_NM", "SCHL_SCSBJT_PROP_NM", "MAIN_SUBJ_NM",
    "MTCLTN_FXNO_CNT", "GRA_CNT", "RELAT_CR_NM", "MDFCN_YMD", "CRTR_YMD",
]

OUT = Path(__file__).parent.parent / "_rawdata" / "major_raw.json"


def fetch_all():
    total = []
    page = 1
    while True:
        params = [("publicDataPk", PUBLIC_DATA_PK)] + [("colNmList", c) for c in COLUMNS] + [
            ("totalCount", "300000"), ("svcTableNm", SVC_TABLE),
            ("perPage", "10000"), ("page", str(page)),
        ]
        data = None
        for attempt in range(5):
            try:
                r = requests.get(BASE, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
                data = r.json()
                break
            except Exception as e:
                print(f"  [재시도 {attempt+1}/5] page {page}: {e}")
                time.sleep(3)
        if data is None:
            print(f"page {page} 최종 실패, 중단")
            break
        if isinstance(data, dict) or not data:
            break
        total.extend(data)
        print(f"page {page}: {len(data)} (cumulative {len(total)})")
        if len(data) < 10000:
            break
        page += 1
        time.sleep(0.3)
    return total


def main():
    items = fetch_all()

    if OUT.exists():
        try:
            old = json.loads(OUT.read_text(encoding="utf-8"))
            if len(items) < len(old) * 0.5:
                print(f"경고: 새 데이터({len(items)})가 기존({len(old)})의 50% 미만 — 저장 중단")
                return
        except Exception:
            pass

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    print(f"\n총 {len(items)}건 저장 → {OUT}")


if __name__ == "__main__":
    main()
