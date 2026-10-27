"""수집·정제 스크립트 공통 함수."""
import re

REGION_RULES = [
    ("전남광주통합특별시", None), ("서울특별시", "서울"), ("서울", "서울"), ("부산광역시", "부산"), ("부산", "부산"),
    ("대구광역시", "대구"), ("대구", "대구"), ("인천광역시", "인천"), ("인천", "인천"), ("광주광역시", "광주"),
    ("대전광역시", "대전"), ("대전", "대전"), ("울산광역시", "울산"), ("울산", "울산"), ("세종특별자치시", "세종"),
    ("세종", "세종"), ("경기도", "경기"), ("경기", "경기"), ("강원특별자치도", "강원"), ("강원도", "강원"), ("강원", "강원"),
    ("충청북도", "충북"), ("충북", "충북"), ("충청남도", "충남"), ("충남", "충남"), ("전북특별자치도", "전북"),
    ("전라북도", "전북"), ("전북", "전북"), ("전라남도", "전남"), ("전남", "전남"), ("경상북도", "경북"),
    ("경북", "경북"), ("경상남도", "경남"), ("경남", "경남"), ("제주특별자치도", "제주"), ("제주", "제주"),
]
# 시도 중심 좌표 (대략). 좌표가 이 지점에서 크게 벗어나면 '지역·좌표 불일치' 검토 대상으로 표시
REGION_CENTER = {
    "서울": (37.56, 126.98), "부산": (35.18, 129.08), "대구": (35.87, 128.60), "인천": (37.46, 126.71),
    "광주": (35.16, 126.85), "대전": (36.35, 127.38), "울산": (35.54, 129.31), "세종": (36.48, 127.29),
    "경기": (37.42, 127.51), "강원": (37.88, 128.16), "충북": (36.64, 127.49), "충남": (36.52, 126.80),
    "전북": (35.82, 127.11), "전남": (34.82, 126.99), "경북": (36.25, 128.73), "경남": (35.46, 128.21),
    "제주": (33.38, 126.55),
}
TEST_PATTERN = re.compile(r"테스트|가상|더미|dummy|sample|\btest\b|lorem", re.IGNORECASE)


# 주소에 시도가 없고 시·군 이름만 있을 때 쓰는 행정구역 대응 (고정된 행정 구역 정보)
CITY_REGION = {"가평군": "경기", "이천시": "경기", "연천군": "경기", "성남시": "경기", "천안시": "충남", "청양군": "충남",
               "경주시": "경북", "구미시": "경북", "성주군": "경북", "울진군": "경북", "양산시": "경남", "거창군": "경남",
               "김해시": "경남", "밀양시": "경남", "달성군": "대구", "나주시": "전남", "함평군": "전남", "진도군": "전남",
               "목포시": "전남", "임실군": "전북"}


def region_of(address):
    """주소 앞부분으로 시도를 정한다. 전남광주통합특별시는 뒤 주소로 광주/전남을 나눈다."""
    if not address:
        return None
    a = address.strip()
    for prefix, region in REGION_RULES:
        if a.startswith(prefix):
            if prefix == "전남광주통합특별시":
                rest = a[len(prefix):].strip()
                return "광주" if rest.startswith("광주") else "전남"
            return region
    return None


def to_float(v):
    try:
        f = float(str(v).strip())
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def to_int_holes(v):
    if v is None:
        return None
    m = re.search(r"\d+", str(v))
    return int(m.group()) if m else None


def clean(v):
    if v is None:
        return None
    s = re.sub(r"\s+", " ", str(v)).strip()
    return None if s in ("", "NULL", "None", "-", "nan") else s


def norm_name(name):
    return re.sub(r"[\s\(\)\[\]·ㆍ-]", "", (name or "")).replace("파크골프장", "").replace("파크골프", "").lower()


def norm_addr(addr):
    return re.sub(r"[\s\-]", "", (addr or "")).replace("번지", "")


def haversine_m(a, b):
    import math
    (la1, lo1), (la2, lo2) = a, b
    r = 6371000
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
