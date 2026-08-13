"""
全球多市场探针系统 - 统一数据层
=================================
提供 Python 友好的数据结构，供程序分析和 FastAPI 接口使用。

数据源优先级: qt.gtimg.cn → hq.sinajs.cn → Yahoo Finance → refine_data
休市自动回退到最近可用数据（缓存永不过期，只在获取到新数据时覆盖）。

用法:
    from api.probe import get_all_probes, get_us_market, get_asia_market

    # 获取全部探针
    data = get_all_probes()  # → dict

    # 按类别获取
    us = get_us_market()     # 美股指数+SOXL
    asia = get_asia_market() # 亚太指数
"""

import json
import re
import time
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, timezone, timedelta

_CST = timezone(timedelta(hours=8))


def _now_cst() -> datetime:
    """当前北京时间"""
    return datetime.now(_CST)

# ============================================================
# 缓存: 永不过期，新数据到达时覆盖。休市时自动使用最近一次成功获取的数据。
# ============================================================

_cache = {}


def _is_fresh(data: dict) -> bool:
    """判断数据是否包含有效价格（非空、非全None）"""
    if not data:
        return False

    def _has_value(d, depth=0):
        if depth > 4:
            return False
        if isinstance(d, (int, float)) and d is not None:
            return True
        if isinstance(d, dict):
            return any(_has_value(v, depth + 1) for v in d.values())
        return False

    return _has_value(data)


def _is_today(date_str: str | None) -> bool:
    """判断日期字符串是否是今天"""
    if not date_str:
        return False
    today = _now_cst().strftime('%Y-%m-%d')
    return date_str == today or date_str.startswith(today)


def _is_trading_hours() -> bool:
    """判断当前是否在A股交易时段（周一到周五 9:15-15:30）"""
    now = _now_cst()
    if now.weekday() >= 5:
        return False
    hour_min = now.hour * 100 + now.minute
    return 915 <= hour_min <= 1530


def _is_us_trading_hours() -> bool:
    """美股交易时段（北京时间 21:30-次日 04:00，夏令时 22:30-次日 05:00）"""
    now = _now_cst()
    if now.weekday() >= 5:
        return False
    hour_min = now.hour * 100 + now.minute
    return hour_min >= 2130 or hour_min <= 400


def _is_asia_trading_hours() -> bool:
    """亚太股市交易时段（北京时间）: 日本/韩国 08:00-14:00, 港股 09:30-16:00"""
    now = _now_cst()
    if now.weekday() >= 5:
        return False
    hour_min = now.hour * 100 + now.minute
    return 800 <= hour_min <= 1600


def _is_commodity_trading_hours() -> bool:
    """商品交易时段（北京时间）: 现货近24小时, 期货 09:00-次日 03:00"""
    now = _now_cst()
    if now.weekday() >= 5:
        return False
    hour_min = now.hour * 100 + now.minute
    return hour_min >= 900 or hour_min <= 300


def _cached_get(category: str) -> dict | None:
    """从缓存获取。任一相关市场在交易时段内时要求日期为今天。"""
    data = _cache.get(category)
    if not data or not _is_fresh(data):
        return None
    is_trading = _is_trading_hours() or _is_us_trading_hours() or _is_asia_trading_hours() or _is_commodity_trading_hours()
    if is_trading:
        dates = []
        def _collect_dates(d, depth=0):
            if depth > 5:
                return
            if isinstance(d, dict):
                if 'date' in d and d['date']:
                    dates.append(d['date'])
                for v in d.values():
                    _collect_dates(v, depth + 1)
            elif isinstance(d, list):
                for v in d:
                    _collect_dates(v, depth + 1)
        _collect_dates(data)
        if dates and not any(_is_today(d) for d in dates):
            return None
    return data


def _cache_set(category: str, data: dict):
    """只有获取到有效数据时才覆盖缓存。"""
    if _is_fresh(data):
        _cache[category] = data


def _invalidate(category: str):
    """强制刷新指定类别。"""
    _cache.pop(category, None)


# ============================================================
# 底层 HTTP 工具
# ============================================================


def _clean_name(name):
    """简化行情名称，去掉冗长后缀"""
    if not name:
        return name
    for suffix in [
        "-Direxion Daily三倍做多",
        "-ProShares三倍做多",
        "-ProShares Ultra三倍做多",
    ]:
        name = name.replace(suffix, "")
    return name


def _fetch_qt(codes: str) -> dict:
    """从腾讯 qt.gtimg.cn 获取行情"""
    url = f"https://qt.gtimg.cn/q={codes}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("gbk", errors="replace")
    except Exception as e:
        return {"_error": str(e)}

    result = {}
    for line in raw.strip().split(";"):
        if not line.strip():
            continue
        m = re.search(r'v_(\w+)="([^"]*)"', line)
        if m:
            code = m.group(1)
            fields = m.group(2).split("~")
            if len(fields) > 32:
                raw_dt = fields[30] if len(fields) > 30 else ""
                if len(raw_dt) >= 8 and raw_dt[:8].isdigit():
                    date = f"{raw_dt[:4]}-{raw_dt[4:6]}-{raw_dt[6:8]}"
                elif len(raw_dt) >= 10:
                    date = raw_dt[:10]
                else:
                    date = None
                result[code] = {
                    "name": _clean_name(fields[1]),
                    "price": _float(fields[3]),
                    "prev_close": _float(fields[4]),
                    "pct": _float(fields[32]),
                    "high": _float(fields[33]) if len(fields) > 33 else None,
                    "low": _float(fields[34]) if len(fields) > 34 else None,
                    "volume": _int(fields[6]) if len(fields) > 6 else None,
                    "date": date,
                }
    return result


def _fetch_sina(codes: str) -> dict:
    """从新浪 hq.sinajs.cn 获取行情"""
    url = f"https://hq.sinajs.cn/list={codes}"
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.sina.com.cn",
            },
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("gbk", errors="replace")
    except Exception as e:
        return {"_error": str(e)}

    result = {}
    for line in raw.strip().split(";"):
        if not line.strip():
            continue
        m = re.search(r'hq_str_(\w+)="([^"]*)"', line)
        if m:
            code = m.group(1)
            fields = m.group(2).split(",")
            if len(fields) < 3:
                continue

            if code.startswith("gb_"):
                try:
                    name = fields[0]
                    price = _float(fields[1])
                    pct = _float(fields[2]) if len(fields) > 2 else 0
                    prev_close = _float(fields[26]) if len(fields) > 26 else None
                except (ValueError, IndexError):
                    continue
                result[code] = {
                    "name": _clean_name(name),
                    "price": price,
                    "pct": pct,
                    "prev_close": prev_close,
                    "date": (
                        f"{fields[29]}-{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(fields[25][:3])+1:02d}-{fields[25][4:6]}"
                        if len(fields) > 29 and len(fields[25]) >= 6
                        else None
                    ),
                }
            elif code.startswith("int_") or code.startswith("b_"):
                try:
                    name = fields[0]
                    price = _float(fields[1]) if len(fields) > 1 else None
                    pct = _float(fields[3]) if len(fields) > 3 else None
                    prev_close = (
                        _float(fields[1]) - _float(fields[2])
                        if len(fields) > 2 and fields[1] and fields[2]
                        else None
                    )
                    if code.startswith("b_") and len(fields) > 6:
                        date = fields[6]
                    elif code.startswith("int_"):
                        date = _now_cst().strftime("%Y-%m-%d")
                    else:
                        date = None
                except (ValueError, IndexError):
                    continue
                result[code] = {
                    "name": name,
                    "price": price,
                    "pct": pct,
                    "prev_close": prev_close,
                    "date": date,
                }
            elif code.startswith("hf_"):
                name = (
                    fields[13]
                    if len(fields) > 13 and fields[13]
                    else (fields[-1] if len(fields) > 4 else code)
                )
                price = _float(fields[0]) if fields[0] else None
                result[code] = {
                    "name": name,
                    "price": price,
                    "prev_close": (
                        _float(fields[1]) if len(fields) > 1 and fields[1] else None
                    ),
                    "date": fields[12] if len(fields) > 12 else None,
                }
            elif code.startswith("fx_"):
                try:
                    result[code] = {
                        "name": fields[9] if len(fields) > 9 else code,
                        "price": _float(fields[1]) if len(fields) > 1 else None,
                        "pct": _float(fields[11]) if len(fields) > 11 else None,
                        "prev_close": (
                            _float(fields[1]) - _float(fields[10])
                            if len(fields) > 10 and fields[1] and fields[10]
                            else None
                        ),
                        "date": fields[17] if len(fields) > 17 else None,
                    }
                except (ValueError, IndexError):
                    continue
            elif code == "DINIW":
                result[code] = {
                    "name": "美元指数",
                    "price": (
                        _float(fields[1])
                        if len(fields) > 1 and fields[1]
                        else _float(fields[0])
                    ),
                    "date": fields[-1] if len(fields) > 1 else None,
                }
    return result


def _float(s):
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _int(s):
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


# ============================================================
# 美股市场
# ============================================================

US_INDICES_QT = {
    "DJI": "usDJI",
    "IXIC": "usIXIC",
    "INX": "usINX",
    "NDX": "usNDX",
    "SOX": "usSOX",
}

US_LEVERAGED_SINA = {
    "SOXL": "gb_soxl",
    "TQQQ": "gb_tqqq",
}

US_TECH_SINA = {
    "NVDA": "gb_nvda",
    "AAPL": "gb_aapl",
    "MSFT": "gb_msft",
    "GOOGL": "gb_googl",
    "AMZN": "gb_amzn",
    "TSLA": "gb_tsla",
}


def get_us_market(force_refresh: bool = False) -> dict:
    cached = None if force_refresh else _cached_get("us")
    if cached:
        return cached

    result = {
        "indices": {},
        "leveraged": {},
        "tech": {},
        "timestamp": _now_cst().isoformat(),
    }

    qt_codes = ",".join(US_INDICES_QT.values())
    qt_data = _fetch_qt(qt_codes)
    for name, code in US_INDICES_QT.items():
        if code in qt_data:
            result["indices"][name] = qt_data[code]

    sina_codes = ",".join(
        list(US_LEVERAGED_SINA.values()) + list(US_TECH_SINA.values())
    )
    sina_data = _fetch_sina(sina_codes)

    for name, code in US_LEVERAGED_SINA.items():
        if code in sina_data:
            result["leveraged"][name] = sina_data[code]

    for name, code in US_TECH_SINA.items():
        if code in sina_data:
            result["tech"][name] = sina_data[code]

    _cache_set("us", result)
    return result


# ============================================================
# 亚太市场
# ============================================================

ASIA_SINA = {
    "N225": "int_nikkei",
    "HSI": "int_hangseng",
    "KOSPI": "b_KOSPI",
    "A50": "hf_XIN",
}

CN_QT = {
    "000001": "sh000001",
    "399001": "sz399001",
    "399006": "sz399006",
    "000300": "sh000300",
    "000905": "sh000905",
    "000688": "sh000688",
}


def get_asia_market(force_refresh: bool = False) -> dict:
    cached = None if force_refresh else _cached_get("asia")
    if cached:
        return cached

    result = {
        "indices": {},
        "futures": {},
        "timestamp": _now_cst().isoformat(),
    }

    sina_codes = ",".join(ASIA_SINA.values())
    sina_data = _fetch_sina(sina_codes)
    for name, code in ASIA_SINA.items():
        if code in sina_data:
            if code.startswith("b_"):
                result["indices"][name] = sina_data[code]
            elif code.startswith("hf_"):
                result["futures"][name] = sina_data[code]
            else:
                result["indices"][name] = sina_data[code]

    _cache_set("asia", result)
    return result


# ============================================================
# 宏观指标
# ============================================================


def get_macro(force_refresh: bool = False) -> dict:
    cached = None if force_refresh else _cached_get("macro")
    if cached:
        return cached

    result = {
        "dxy": None,
        "usdcnh": None,
        "timestamp": _now_cst().isoformat(),
    }

    sina = _fetch_sina("DINIW")
    if "DINIW" in sina:
        result["dxy"] = sina["DINIW"]

    cn = _fetch_sina("fx_susdcnh")
    if "fx_susdcnh" in cn:
        result["usdcnh"] = cn["fx_susdcnh"]
    else:
        result["usdcnh"] = {"name": "USD/CNH", "price": None, "_note": "unavailable"}

    _cache_set("macro", result)
    return result


# ============================================================
# 商品
# ============================================================

COMMODITY_SINA = {
    "XAU": "hf_XAU",
    "XAG": "hf_XAG",
    "CL": "hf_CL",
}

COMMODITY_QT = {
    "GC": "fuGC",
    "SI": "fuSI",
    "CLF": "fuCL",
}

# 上海金（东财 secid）
SHANGHAI_GOLD_SECID = "118.AU9999"
# 黄金ETF
GOLD_ETF_CODE = "518880"
# 盎司转克
OZ_TO_G = 31.1035


def _fetch_em_secid(secid: str) -> dict | None:
    """从东财 push2 获取单个 secid 行情，价格按 f59 小数位数转换"""
    url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f57,f58,f43,f170,f44,f45,f59"
    try:
        import subprocess
        r = subprocess.run(
            ['curl', '-fsS', '--retry', '3', '--http1.1', '-A', 'Mozilla/5.0', url],
            capture_output=True, text=True, timeout=10,
        )
        d = json.loads(r.stdout).get('data')
        if d:
            decimals = int(d.get('f59') or 2)
            factor = 10 ** decimals
            return {
                'name': d.get('f58', ''),
                'price': _float(d.get('f43')) / factor,
                'prev_close': _float(d.get('f44')) / factor,
                'pct': _float(d.get('f170')) / 100,
            }
    except Exception:
        pass
    return None


def get_commodities(force_refresh: bool = False) -> dict:
    cached = None if force_refresh else _cached_get("commodity")
    if cached:
        return cached

    result = {
        "spot": {},
        "futures": {},
        "timestamp": _now_cst().isoformat(),
    }

    sina_codes = ",".join(COMMODITY_SINA.values())
    sina_data = _fetch_sina(sina_codes)
    for name, code in COMMODITY_SINA.items():
        item = sina_data.get(code)
        if item and item.get("price") and item.get("name") not in ("0", "", None):
            result["spot"][name] = item

    qt_codes = ",".join(COMMODITY_QT.values())
    qt_data = _fetch_qt(qt_codes)
    for name, code in COMMODITY_QT.items():
        item = qt_data.get(code)
        if item and item.get("price") and item.get("name") not in ("0", "", None):
            result["futures"][name] = item

    # 获取离岸人民币汇率
    cnh_data = _fetch_sina("fx_susdcnh")
    usdcnh = cnh_data.get("fx_susdcnh", {}).get("price") if cnh_data else None

    # 上海金
    shgold = _fetch_em_secid(SHANGHAI_GOLD_SECID)
    if shgold:
        shgold["name"] = "AU9999"
        result["spot"]["SHGOLD"] = shgold

    # 黄金ETF（净值≈金价/100，所以折算 = 价格×100）
    gold_etf = _fetch_em_secid(f"1.{GOLD_ETF_CODE}")
    if gold_etf:
        gold_etf["name"] = "黄金ETF"
        result["spot"]["GOLDETF"] = gold_etf

    # 人民币折算（美元/盎司 → 人民币/克）
    if usdcnh:
        for key in ("XAU", "GC"):
            item = result["spot"].get(key) or result["futures"].get(key)
            if item and item.get("price"):
                item["cny_per_gram"] = round(item["price"] / OZ_TO_G * usdcnh, 2)
        # 黄金ETF 折算：每份≈0.00951克黄金
        if result["spot"].get("GOLDETF"):
            result["spot"]["GOLDETF"]["cny_per_gram"] = round(result["spot"]["GOLDETF"]["price"] / 0.00951, 2)

    _cache_set("commodity", result)
    return result


# ============================================================
# 统一入口
# ============================================================


def get_cn_indices(force_refresh: bool = False) -> dict:
    cached = None if force_refresh else _cached_get("cn")
    if cached:
        return cached

    result = {"indices": {}, "timestamp": _now_cst().isoformat()}
    qt_codes = ",".join(CN_QT.values())
    qt_data = _fetch_qt(qt_codes)
    for name, code in CN_QT.items():
        if code in qt_data:
            result["indices"][name] = qt_data[code]

    _cache_set("cn", result)
    return result


def get_margin_trading(force_refresh: bool = False) -> dict:
    """融资融券: 两市融资余额/融券余额/融资融券余额"""
    cached = None if force_refresh else _cached_get("margin")
    if cached:
        return cached

    result = {"data": None, "timestamp": _now_cst().isoformat()}
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get"
        "?reportName=RPTA_RZRQ_LSHJ"
        "&columns=DIM_DATE,RZYE,RQYE,RZRQYE,RZMRE,RQJMG"
        "&source=WEB&sortColumns=DIM_DATE&sortTypes=-1&pageSize=5"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        items = (payload.get("result") or {}).get("data") or []
        if items:
            latest = items[0]
            prev = items[1] if len(items) > 1 else {}
            rzye = _float(latest.get("RZYE"))
            prev_rzye = _float(prev.get("RZYE")) if prev else 0
            result["data"] = {
                "date": latest["DIM_DATE"][:10],
                "rzye": rzye,
                "rqye": _float(latest.get("RQYE")),
                "rzrqye": _float(latest.get("RZRQYE")),
                "rzmr": _float(latest.get("RZMRE")),
                "rzmr_pct": (
                    ((rzye - prev_rzye) / prev_rzye * 100) if prev_rzye else None
                ),
            }
    except Exception:
        pass

    _cache_set("margin", result)
    return result


def get_capital_flow(force_refresh: bool = False) -> dict:
    """大盘资金流向: 上证/深证主力净流入、超大单、大单、中单、小单（交易中取实时，收盘后取日K）"""
    cached = None if force_refresh else _cached_get('capital_flow')
    if cached:
        return cached

    result = {'data': [], 'timestamp': _now_cst().isoformat()}
    codes = {'000001': '上证指数', '399001': '深证成指'}
    is_trading = _is_trading_hours()
    for code, name in codes.items():
        market = '1' if code.startswith('5') or code.startswith('0') else '0'
        if is_trading:
            url = (
                f'http://push2.eastmoney.com/api/qt/stock/fflow/kline/get'
                f'?secid={market}.{code}'
                f'&fields1=f1,f2,f3,f7'
                f'&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63'
                f'&klt=1&lmt=1'
            )
        else:
            url = (
                f'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get'
                f'?secid={market}.{code}'
                f'&fields1=f1,f2,f3,f7'
                f'&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63'
                f'&klt=101&lmt=1'
            )
        try:
            import subprocess
            r = subprocess.run(
                ['curl', '-fsS', '--retry', '3', '--retry-delay', '1', '--http1.1',
                 '-A', 'Mozilla/5.0', url],
                capture_output=True, text=True, timeout=15,
            )
            payload = json.loads(r.stdout)
            klines = (payload.get('data') or {}).get('klines') or []
            if klines:
                fields = klines[-1].split(',')
                if is_trading:
                    # 分时数据: [时间, 主力, 超大单, 大单, 中单, 小单]
                    result['data'].append({
                        'code': code,
                        'name': name,
                        'date': fields[0].split(' ')[0],
                        'time': fields[0].split(' ')[1] if ' ' in fields[0] else '',
                        'main': _float(fields[1]),
                        'super_large': _float(fields[2]),
                        'large': _float(fields[3]),
                        'medium': _float(fields[4]),
                        'small': _float(fields[5]),
                        'main_pct': None,
                        'close': None,
                        'pct': None,
                    })
                else:
                    # 日K数据: [日期, 主力, 超大单, 大单, 中单, 小单, 主力占比%, ..., 收盘价, 涨跌幅%]
                    result['data'].append({
                        'code': code,
                        'name': name,
                        'date': fields[0],
                        'time': '',
                        'main': _float(fields[1]),
                        'super_large': _float(fields[2]),
                        'large': _float(fields[3]),
                        'medium': _float(fields[4]),
                        'small': _float(fields[5]),
                        'main_pct': _float(fields[6]),
                        'close': _float(fields[11]),
                        'pct': _float(fields[12]),
                    })
        except Exception:
            pass

    _cache_set('capital_flow', result)
    return result


def get_hk_connect(force_refresh: bool = False) -> dict:
    """港股通: 北向沪股通/深股通 + 南向港股通(沪)/(深)"""
    cached = None if force_refresh else _cached_get("hk_connect")
    if cached:
        return cached

    result = {"data": [], "timestamp": _now_cst().isoformat()}
    url = (
        "https://datacenter-web.eastmoney.com/api/data/v1/get"
        "?reportName=RPT_MUTUAL_DEAL_HISTORY"
        "&columns=ALL&source=WEB&sortColumns=TRADE_DATE&sortTypes=-1&pageSize=6"
    )
    type_names = {
        "001": "北向沪股通",
        "003": "北向深股通",
        "002": "南向港股通(沪)",
        "004": "南向港股通(深)",
    }
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        items = (payload.get("result") or {}).get("data") or []
        seen = set()
        for item in items:
            mtype = item.get("MUTUAL_TYPE", "")
            if mtype not in type_names or mtype in seen:
                continue
            seen.add(mtype)
            result["data"].append(
                {
                    "type": type_names[mtype],
                    "date": item["TRADE_DATE"][:10],
                    "deal_amt": _float(item.get("DEAL_AMT")) or 0,
                    "net_buy": _float(item.get("NET_DEAL_AMT")),
                }
            )
    except Exception:
        pass

    _cache_set("hk_connect", result)
    return result


def get_all_probes(force_refresh: bool = False) -> dict:
    cached = None if force_refresh else _cached_get("all")
    if cached:
        return cached

    result = {
        "us": get_us_market(force_refresh),
        "asia": get_asia_market(force_refresh),
        "cn": get_cn_indices(force_refresh),
        "margin": get_margin_trading(force_refresh),
        "hk_connect": get_hk_connect(force_refresh),
        "macro": get_macro(force_refresh),
        "commodities": get_commodities(force_refresh),
        "timestamp": _now_cst().isoformat(),
    }

    _cache_set("all", result)
    return result
