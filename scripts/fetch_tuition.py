"""
fetch_tuition.py — 전국 대학별 평균등록금 표준데이터 다운로드 (한국장학재단, publicDataPk=15107738)
data.go.kr download/standard.json 직접 다운로드 (API 키 불필요), svcTableNm=tn_pubr_public_univ_reg_amt_api
2026-10-29 확인: 946행(대학 438곳 × 구분), 기준일 2026-05-19
"""
import json
from pathlib import Path
import requests

COLS = ["CRTR_YR", "CTPV_CD", "CTPV_NM", "UNIV_SE_NM", "UNIV_NM", "MAINBRANCH_NM", "FNDN_FORM_SE_NM", "AVG_MTCLTN_AMT", "AVG_REG_AMT", "CRTR_YMD"]
OUT = Path(__file__).parent.parent / "_rawdata_tuition" / "tuition_raw.json"
params = [("publicDataPk", "15107738")] + [("colNmList", c) for c in COLS] + [("totalCount", "5000"), ("svcTableNm", "tn_pubr_public_univ_reg_amt_api"), ("perPage", "2000"), ("page", "1")]
r = requests.get("https://www.data.go.kr/download/standard.json", params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
d = r.json()
OUT.parent.mkdir(exist_ok=True)
json.dump(d, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
print(len(d), "rows")
