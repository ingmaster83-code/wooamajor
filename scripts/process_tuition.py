"""
process_tuition.py — 한국장학재단 대학별 평균등록금(표준데이터 15107738) → 등록금 페이지 정의

입력: _rawdata_tuition/tuition_raw.json (fetch_tuition.py), _rawdata/schools_*.json (학교 슬러그 매칭용)
출력: _rawdata/tuition_pages.json (페이지 목록, major_generator.rb 의 TuitionGenerator 가 읽음)
      _rawdata/tuition_by_school.json (학교 페이지 → 등록금 페이지 링크)
2026-10-29
"""
import json, re, glob, collections
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW = ROOT / "_rawdata_tuition" / "tuition_raw.json"
OUT = ROOT / "_rawdata" / "tuition_pages.json"
OUT_SCHOOL = ROOT / "_rawdata" / "tuition_by_school.json"

LEVEL_ORDER = ["대학", "전문대학", "원격대학", "일반대학원", "특수대학원", "전문대학원"]
LEVEL_LABEL = {"대학": "대학(학부)", "전문대학": "전문대학", "원격대학": "원격대학(사이버대)", "일반대학원": "일반대학원", "특수대학원": "특수대학원", "전문대학원": "전문대학원"}
UNDER = ["대학", "전문대학", "원격대학"]


def man(v):  # 원 → "609만 원"
    return "{:,}만 원".format(int(round(v / 10000.0)))


def won(v):
    return "{:,}원".format(int(round(v)))


def slugify(text):
    s = re.sub(r"[^\w가-힣\s-]", " ", text)
    s = re.sub(r"\s+", "-", s.strip())
    return re.sub(r"-+", "-", s)


rows = json.load(open(RAW, encoding="utf-8"))
recs = []
for r in rows:
    try:
        reg = float(r["AVG_REG_AMT"]); adm = float(r["AVG_MTCLTN_AMT"])
    except Exception:
        continue
    if reg <= 0:
        continue
    recs.append({"univ": r["UNIV_NM"].strip(), "level": r["UNIV_SE_NM"], "campus": r["MAINBRANCH_NM"], "type": r["FNDN_FORM_SE_NM"],
                 "region": r["CTPV_NM"], "reg": reg, "adm": adm, "date": r["CRTR_YMD"]})

# 학교 슬러그 매칭
school_slug = {}
for f in glob.glob(str(ROOT / "_rawdata" / "schools_*.json")):
    for s in json.load(open(f, encoding="utf-8")):
        school_slug[s["schoolName"]] = s["slug"]

by_univ = collections.defaultdict(list)
for r in recs:
    by_univ[r["univ"]].append(r)

used = set(); spath = {}
for u in sorted(by_univ):
    base = slugify(u) or "univ"
    sl = base; i = 2
    while sl in used:
        sl = "%s-%d" % (base, i); i += 1
    used.add(sl); spath[u] = "/tuition/%s/" % sl

ASOF = max(r["date"] for r in recs)


def lead_row(u):
    rs = by_univ[u]
    for lv in LEVEL_ORDER:
        c = [r for r in rs if r["level"] == lv]
        if c:
            c.sort(key=lambda r: (r["campus"] != "본교", -r["reg"]))
            return c[0]


# 순위: (level, type-group) 별
def rank_table(level, types=None):
    xs = [r for r in recs if r["level"] == level and (types is None or r["type"] in types)]
    return xs

RANK_ALL = {}
for lv in LEVEL_ORDER:
    xs = sorted([r for r in recs if r["level"] == lv], key=lambda r: -r["reg"])
    RANK_ALL[lv] = {(r["univ"], r["campus"]): i + 1 for i, r in enumerate(xs)}
    RANK_ALL[lv]["_n"] = len(xs)
    RANK_ALL[lv]["_avg"] = sum(r["reg"] for r in xs) / max(1, len(xs))

pages = []
school_links = {}


def disp_name(r):
    return r["univ"] + ("" if r["campus"] == "본교" else " (%s)" % r["campus"])


for u in sorted(by_univ):
    rs = by_univ[u]; lr = lead_row(u); lv = lr["level"]
    ptype = lr["type"]; region = lr["region"]
    n = RANK_ALL[lv]["_n"]; rk = RANK_ALL[lv][(u, lr["campus"])]
    avg = RANK_ALL[lv]["_avg"]; diff = (lr["reg"] / avg - 1) * 100
    lvl = LEVEL_LABEL[lv]
    lead = "%s(%s·%s)의 %s 평균 등록금은 연 <b>%s</b>(학기당 약 %s)입니다." % (u, ptype, region, lvl, man(lr["reg"]), man(lr["reg"] / 2))
    if lr["adm"] > 0:
        lead += " 평균 입학금은 %s입니다." % man(lr["adm"])
    else:
        lead += " 평균 입학금은 0원으로 집계됩니다."
    lead += " 전국 %s %d곳 중 등록금이 높은 순으로 %d위이며, 전체 평균(연 %s)보다 %.1f%% %s." % (lvl, n, rk, man(avg), abs(diff), "높습니다" if diff > 0 else "낮습니다")
    table = []
    for lv2 in LEVEL_ORDER:
        for r in sorted([x for x in rs if x["level"] == lv2], key=lambda r: (r["campus"] != "본교", r["campus"])):
            table.append({"level": LEVEL_LABEL[lv2], "campus": r["campus"], "adm": won(r["adm"]) if r["adm"] > 0 else "없음(0원)", "reg": won(r["reg"]), "sem": won(r["reg"] / 2)})
    peers = [x for x in recs if x["level"] == lv and x["region"] == region and x["univ"] != u and x["campus"] == "본교"]
    peers.sort(key=lambda x: abs(x["reg"] - lr["reg"]))
    peer_rows = [{"label": disp_name(x), "href": spath[x["univ"]], "type": x["type"], "reg": man(x["reg"])} for x in peers[:8]]
    faq = [
        {"q": "%s 등록금은 얼마인가요?" % u, "a": "%s 기준 %s %s 평균 등록금은 연 %s(학기당 약 %s)입니다. 학과(계열)에 따라 실제 금액은 다를 수 있습니다." % (ASOF[:4] + "년", u, lvl, man(lr["reg"]), man(lr["reg"] / 2))},
        {"q": "%s 입학금이 있나요?" % u, "a": ("평균 입학금은 %s입니다." % man(lr["adm"])) if lr["adm"] > 0 else "한국장학재단 집계상 평균 입학금은 0원입니다. 입학금은 대학별로 단계적으로 폐지되어 왔으며, 정확한 금액은 학교 공고에서 확인하세요."},
        {"q": "%s 등록금은 다른 대학보다 비싼가요?" % u, "a": "전국 %s %d곳 중 등록금이 높은 순으로 %d위이고, 전체 평균(연 %s)보다 %.1f%% %s." % (lvl, n, rk, man(avg), abs(diff), "높습니다" if diff > 0 else "낮습니다")},
    ]
    title = "%s 등록금 %s — 연 %s·입학금" % (u, ASOF[:4], man(lr["reg"]))
    desc = "%s %s 평균 등록금 연 %s(학기당 약 %s), 입학금, 전국 순위와 같은 지역 대학 비교. 한국장학재단 %s 기준." % (u, lvl, man(lr["reg"]), man(lr["reg"] / 2), ASOF)
    pages.append({"path": spath[u], "layout": "tuition_univ", "title": title, "description": desc[:155],
                  "data": {"univName": u, "lead": lead, "table": table, "peers": peer_rows, "faq": faq, "ptype": ptype, "region": region,
                           "levelLabel": lvl, "rank": rk, "total": n, "reg": man(lr["reg"]), "sem": man(lr["reg"] / 2), "asof": ASOF,
                           "schoolHref": ("/school/%s/" % school_slug[u]) if u in school_slug else ""}})
    if u in school_slug and lv in UNDER:
        school_links[school_slug[u]] = {"url": spath[u], "text": "%s %s 평균 등록금 연 %s (학기당 약 %s)" % (u, lvl, man(lr["reg"]), man(lr["reg"] / 2))}


def rank_rows(xs, key):
    xs = sorted(xs, key=key)
    return [{"rank": i + 1, "label": disp_name(r), "href": spath[r["univ"]], "type": r["type"], "region": r["region"], "reg": man(r["reg"]), "sem": man(r["reg"] / 2), "adm": man(r["adm"]) if r["adm"] > 0 else "없음"} for i, r in enumerate(xs)]


def add_rank(slug, title, h1, lead, xs, desc_key, reverse=True, desc=None):
    key = (lambda r: -r["reg"]) if reverse else (lambda r: r["reg"])
    rr = rank_rows(xs, key)
    pages.append({"path": "/tuition/rank/%s/" % slug, "layout": "tuition_list", "title": title, "description": (desc or lead)[:155],
                  "data": {"h1": h1, "lead": lead, "rows": rr, "asof": ASOF, "kind": "rank"}})

U4 = [r for r in recs if r["level"] == "대학"]
U2 = [r for r in recs if r["level"] == "전문대학"]
G = [r for r in recs if r["level"] == "일반대학원"]
avg = lambda xs: sum(r["reg"] for r in xs) / max(1, len(xs))
nat = [r for r in U4 if r["type"] in ("국립", "공립")]; pri = [r for r in U4 if r["type"] == "사립"]
add_rank("univ-high", "대학교 등록금 순위 %s — 비싼 대학 TOP" % ASOF[:4], "대학교 등록금 순위 — 비싼 순", "전국 4년제 대학 %d곳(캠퍼스 포함)의 %s 평균 등록금을 높은 순으로 정리했습니다. 전체 평균은 연 %s입니다." % (len(U4), ASOF[:4] + "년", man(avg(U4))), U4, "h")
add_rank("univ-low", "대학교 등록금 싼 곳 순위 %s — 저렴한 대학" % ASOF[:4], "대학교 등록금 순위 — 저렴한 순", "전국 4년제 대학 %d곳의 평균 등록금을 낮은 순으로 정리했습니다. 국공립대는 사립대보다 평균 %s 낮습니다." % (len(U4), man(avg(pri) - avg(nat))), U4, "l", reverse=False)
add_rank("national", "국공립대 등록금 순위 %s — 국립대 평균 등록금" % ASOF[:4], "국공립대학교 등록금 순위", "국공립 4년제 대학 %d곳의 평균 등록금은 연 %s입니다. 높은 순으로 정리했습니다." % (len(nat), man(avg(nat))), nat, "n")
add_rank("private", "사립대 등록금 순위 %s — 사립대학교 평균 등록금" % ASOF[:4], "사립대학교 등록금 순위", "사립 4년제 대학 %d곳의 평균 등록금은 연 %s입니다. 높은 순으로 정리했습니다." % (len(pri), man(avg(pri))), pri, "p")
add_rank("college-high", "전문대학 등록금 순위 %s — 비싼 전문대" % ASOF[:4], "전문대학 등록금 순위 — 비싼 순", "전국 전문대학 %d곳의 평균 등록금을 높은 순으로 정리했습니다. 전체 평균은 연 %s입니다." % (len(U2), man(avg(U2))), U2, "ch")
add_rank("college-low", "전문대학 등록금 싼 곳 순위 %s" % ASOF[:4], "전문대학 등록금 순위 — 저렴한 순", "전국 전문대학 %d곳의 평균 등록금을 낮은 순으로 정리했습니다." % len(U2), U2, "cl", reverse=False)
add_rank("grad-high", "대학원 등록금 순위 %s — 일반대학원 평균 등록금" % ASOF[:4], "일반대학원 등록금 순위", "일반대학원 %d곳의 평균 등록금(연)을 높은 순으로 정리했습니다. 전체 평균은 연 %s입니다." % (len(G), man(avg(G))), G, "g")

# 시도별
regions = sorted({r["region"] for r in U4 + U2})
reg_summary = []
for rg in regions:
    a = [r for r in U4 if r["region"] == rg]; b = [r for r in U2 if r["region"] == rg]
    path = "/tuition/region/%s/" % rg
    rr = rank_rows(a, lambda r: -r["reg"]); rr2 = rank_rows(b, lambda r: -r["reg"])
    lead = "%s 소재 4년제 대학 %d곳의 평균 등록금은 연 %s" % (rg, len(a), man(avg(a))) if a else "%s에는 4년제 대학 등록금 집계가 없습니다" % rg
    if b: lead += ", 전문대학 %d곳은 연 %s입니다." % (len(b), man(avg(b)))
    else: lead += "입니다."
    pages.append({"path": path, "layout": "tuition_list", "title": "%s 대학교 등록금 %s — 지역 대학 비교" % (rg, ASOF[:4]), "description": lead[:155],
                  "data": {"h1": "%s 대학교 등록금" % rg, "lead": lead, "rows": rr, "rows2": rr2, "asof": ASOF, "kind": "region"}})
    reg_summary.append({"label": rg, "href": path, "n": len(a) + len(b), "avg": man(avg(a)) if a else "-"})

# 허브
hub_lead = "전국 대학 %d곳의 %s 평균 등록금(한국장학재단 공시 %s 기준)입니다. 4년제 대학 평균은 연 %s(국공립 %s, 사립 %s), 전문대학 평균은 연 %s입니다." % (len(by_univ), ASOF[:4] + "년", ASOF, man(avg(U4)), man(avg(nat)), man(avg(pri)), man(avg(U2)))
hub_rows = rank_rows([r for r in recs if r["level"] in ("대학", "전문대학", "원격대학") and r["campus"] == "본교"], lambda r: r["univ"])
pages.append({"path": "/tuition/", "layout": "tuition_list", "title": "대학교 등록금 %s — 전국 대학 평균 등록금·입학금 비교" % ASOF[:4], "description": hub_lead[:155],
              "data": {"h1": "전국 대학교 등록금", "lead": hub_lead, "rows": hub_rows, "regions": reg_summary, "asof": ASOF, "kind": "hub"}})

json.dump(pages, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
json.dump(school_links, open(OUT_SCHOOL, "w", encoding="utf-8"), ensure_ascii=False)
print("pages", len(pages), "universities", len(by_univ), "school links", len(school_links), "asof", ASOF)
