"""서울 열린데이터광장 실시간 API 세 개를 불러 index.html 안의 데이터 줄을 바꾼다.

- S-DoT 환경정보(sDoTEnv): 행정동별 지금 기온·습도  -> window.SDOT_NOW
- 실시간 도시데이터(citydata): 주요 장소 혼잡도·예측  -> window.CITY_NOW
- 권역별 실시간 대기환경(RealtimeCityAir) + 서울 평균 -> window.AIR_NOW

인증키는 환경변수 SEOUL_API_KEY 에서 읽는다 (GitHub 저장소 Settings > Secrets).
파이썬 표준 라이브러리만 쓴다. 하나가 실패해도 나머지는 갱신한다.
"""
import csv, json, os, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

KEY = os.environ.get("SEOUL_API_KEY", "").strip()
HTML = "index.html"
if not KEY:
    sys.exit("SEOUL_API_KEY 가 비어 있습니다.")


def api(svc, a, b, extra=""):
    url = f"http://openapi.seoul.go.kr:8088/{KEY}/json/{svc}/{a}/{b}/{extra}"
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:  # 잠깐 끊기면 다시 시도
            err = e
            time.sleep(2 * (i + 1))
    raise err


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def js(name, obj):
    return f"window.{name}=" + json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + ";"


GU = {"Jongno": "종로구", "Jung": "중구", "Yongsan": "용산구", "Seongdong": "성동구", "Gwangjin": "광진구",
      "Dongdaemun": "동대문구", "Jungnang": "중랑구", "Seongbuk": "성북구", "Gangbuk": "강북구", "Dobong": "도봉구",
      "Nowon": "노원구", "Eunpyeong": "은평구", "Seodaemun": "서대문구", "Mapo": "마포구", "Yangcheon": "양천구",
      "Gangseo": "강서구", "Guro": "구로구", "Geumcheon": "금천구", "Yeongdeungpo": "영등포구", "Dongjak": "동작구",
      "Gwanak": "관악구", "Seocho": "서초구", "Gangnam": "강남구", "Songpa": "송파구", "Gangdong": "강동구"}


def sdot():
    rows = []
    for a, b in ((1, 1000), (1001, 2000)):
        rows += api("sDoTEnv", a, b)["sDoTEnv"]["row"]
    latest = {}
    for r in rows:
        t = num(r.get("AVG_TEMP"))
        if t is None or not -40 < t < 60:
            continue
        p = latest.get(r["SERIAL"])
        if not p or r["SENSING_TIME"] > p["SENSING_TIME"]:
            latest[r["SERIAL"]] = r
    by_serial, by_name = {}, {}
    with open("data/sdot_sensor_dong.csv", encoding="utf-8-sig") as f:
        for m in csv.DictReader(f):
            by_serial[m["serial"]] = m["code"]
            by_name.setdefault((m["gu"], m["dong_en"]), m["code"])
    acc, n, tmax = {}, 0, ""
    for r in latest.values():
        gu = GU.get(r["AUTONOMOUS_DISTRICT"].replace("-gu", ""))
        code = by_serial.get(r["SERIAL"]) or by_name.get((gu, r["ADMINISTRATIVE_DISTRICT"]))
        if not code:
            continue
        a = acc.setdefault(code, [0, 0, 0, 0])
        a[0] += num(r["AVG_TEMP"]); a[1] += 1
        h = num(r.get("AVG_HUMI"))
        if h is not None:
            a[2] += h; a[3] += 1
        n += 1
        tmax = max(tmax, r["SENSING_TIME"])
    d = {k: [round(a[0] / a[1], 1), round(a[2] / a[3]) if a[3] else None, a[1]] for k, a in acc.items()}
    t = tmax.replace("_", " ")[:16]
    print(f"S-DoT: 센서 {n}개, 행정동 {len(d)}곳, {t}")
    return js("SDOT_NOW", {"t": t, "n": n, "d": d})


LV = {"여유": 0, "보통": 1, "약간 붐빔": 2, "붐빔": 3}


def one_place(i):
    try:
        c = api("citydata", 1, 5, f"POI{i:03d}").get("CITYDATA")
    except Exception:
        return None
    if not c:
        return None
    p = (c.get("LIVE_PPLTN_STTS") or [{}])[0]
    w = (c.get("WEATHER_STTS") or [{}])[0]
    pts = [(num(b.get("SBIKE_Y")), num(b.get("SBIKE_X"))) for b in c.get("SBIKE_STTS") or []]
    if not pts:
        pts = [(num(b.get("BUS_STN_Y")), num(b.get("BUS_STN_X"))) for b in c.get("BUS_STN_STTS") or []]
    if not pts:
        pts = [(num(b.get("LAT")), num(b.get("LNG"))) for b in c.get("PRK_STTS") or []]
    pts = [q for q in pts if q[0] and q[1] and 37 < q[0] < 38 and 126 < q[1] < 128]
    if not pts or p.get("AREA_CONGEST_LVL") not in LV:
        return None
    fc = p.get("FCST_PPLTN") or []
    return {"i": i, "time": p.get("PPLTN_TIME"), "f0": int(fc[0]["FCST_TIME"][11:13]) if fc else None,
            "row": [c["AREA_NM"], round(sum(q[0] for q in pts) / len(pts), 5), round(sum(q[1] for q in pts) / len(pts), 5),
                    LV[p["AREA_CONGEST_LVL"]], int(num(p.get("AREA_PPLTN_MIN")) or 0), int(num(p.get("AREA_PPLTN_MAX")) or 0),
                    "".join(str(LV.get(x.get("FCST_CONGEST_LVL"), 0)) for x in fc),
                    num(w.get("TEMP")), int(num(w.get("HUMIDITY"))) if num(w.get("HUMIDITY")) is not None else None]}


def city():
    with ThreadPoolExecutor(6) as ex:
        res = [r for r in ex.map(one_place, range(1, 136)) if r]
    res.sort(key=lambda r: r["i"])
    if not res:
        raise RuntimeError("장소를 하나도 받지 못했습니다")
    print(f"도시데이터: 장소 {len(res)}곳, {res[0]['time']}")
    return js("CITY_NOW", {"t": res[0]["time"], "f0": next((r["f0"] for r in res if r["f0"] is not None), 0), "p": [r["row"] for r in res]})


def air():
    rows = api("RealtimeCityAir", 1, 25)["RealtimeCityAir"]["row"]
    z = lambda v: (num(v) if num(v) and num(v) > 0 else None)
    g = {r["MSRSTN_NM"]: [z(r.get("PM")), z(r.get("FPM")), z(r.get("OZON")), r.get("CAI_GRD") or None, z(r.get("CAI_IDX"))] for r in rows}
    for v in g.values():
        for j in (0, 1, 4):
            if v[j] is not None:
                v[j] = int(v[j])
    dt = rows[0]["MSRMT_DT"]
    t = f"{dt[:4]}-{dt[4:6]}-{dt[6:8]} {dt[8:10]}:{dt[10:12]}"
    try:
        a = api("ListAvgOfSeoulAirQualityService", 1, 1)["ListAvgOfSeoulAirQualityService"]["row"][0]
        avg = [z(a.get("PM")), z(a.get("FPM")), z(a.get("OZON"))]
    except Exception:
        avg = None
    print(f"대기질: 자치구 {len(g)}곳, {t}")
    return js("AIR_NOW", {"t": t, "avg": avg, "g": g})


html = open(HTML, encoding="utf-8").read()
changed = 0
for name, fn in (("SDOT_NOW", sdot), ("CITY_NOW", city), ("AIR_NOW", air)):
    try:
        line = fn()
    except Exception as e:
        print(f"{name} 갱신 실패: {e}")
        continue
    html, k = re.subn(rf"^window\.{name}=.*$", lambda m: line, html, count=1, flags=re.M)
    changed += k
open(HTML, "w", encoding="utf-8").write(html)
print(f"완료: {changed}개 항목 갱신")
if not changed:
    sys.exit(1)
