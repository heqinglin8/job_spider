"""
广东公共求职招聘服务平台 爬虫脚本
目标网站: https://ggfw.hrss.gd.gov.cn/recruitment/internet/main/#/search

API 说明:
- 职位列表: POST /recruitment/internet/main/internet/retrieval/c/recruitment/homepage/positions
- 职位详情: GET  /recruitment/internet/main/internet/r/c/webpage/homepage/position/detail/{id}
"""

import time
import json
import csv
import logging
import argparse
import os
from datetime import datetime
from typing import Optional

import requests

# ──────────────────────────────────────────────────────────────────────
# 基础配置
# ──────────────────────────────────────────────────────────────────────

BASE_URL = "https://ggfw.hrss.gd.gov.cn/recruitment/internet/main"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Referer": "https://ggfw.hrss.gd.gov.cn/recruitment/internet/main/",
    "Origin": "https://ggfw.hrss.gd.gov.cn",
}

# 广东省各市城市代码
CITY_CODES = {
    "广州": "440100000000",
    "韶关": "440200000000",
    "深圳": "440300000000",
    "珠海": "440400000000",
    "汕头": "440500000000",
    "佛山": "440600000000",
    "江门": "440700000000",
    "湛江": "440800000000",
    "茂名": "440900000000",
    "肇庆": "441200000000",
    "惠州": "441300000000",
    "梅州": "441400000000",
    "汕尾": "441500000000",
    "河源": "441600000000",
    "阳江": "441700000000",
    "清远": "441800000000",
    "东莞": "441900000000",
    "中山": "442000000000",
    "潮州": "445100000000",
    "揭州": "445200000000",
    "云浮": "445300000000",
}

PAGE_SIZE = 10          # API 实际每页返回条数（发送更大值也只返回10条）
REQUEST_DELAY = 0.5     # 请求间隔秒数，避免过于频繁
MAX_PAGES_PER_CITY = 50 # 单城市最多抓取页数 (API 上限约 1000 条)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# 登录检测 & 浏览器登录
# ──────────────────────────────────────────────────────────────────────

MAIN_URL = "https://ggfw.hrss.gd.gov.cn/recruitment/internet/main/"
_CHECK_CITY_CODE = "440100000000"   # 用广州职位验证登录（数据量大，容易抽到有电话的职位）
_CHECK_SAMPLE_SIZE = 5              # 验证登录时最多抽取的样本数


def check_login(session: requests.Session) -> bool:
    """检测当前 session 是否已登录（能否从详情接口取到联系电话）。

    联系电话(aae005)只有登录后才会返回。单条职位可能本身未填写电话，
    因此抽取多条样本，只要有一条有电话即视为已登录。
    """
    try:
        data = fetch_position_list(session, _CHECK_CITY_CODE, page_num=1, page_size=_CHECK_SAMPLE_SIZE)
        records = data.get("records", [])
        if not records:
            return True  # 无数据无法判断，放行

        for rec in records:
            position_id = rec.get("bcb009", "")
            if not position_id:
                continue
            detail = fetch_position_detail(session, position_id)
            if detail.get("aae005", ""):
                return True  # 找到有电话的职位，确认已登录
            time.sleep(0.3)

        # 所有样本均无联系电话，判定为未登录
        logger.debug(f"抽取 {len(records)} 条样本，均无联系电话，判定未登录")
        return False
    except Exception as exc:
        logger.debug(f"登录检测异常: {exc}")
        return False


def browser_login(session: requests.Session) -> None:
    """弹出 Chromium 浏览器让用户手动登录，登录后将 cookies 注入 session。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise ImportError(
            "需要安装 playwright 才能弹出浏览器登录：\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        ) from exc

    logger.info(f"正在打开浏览器: {MAIN_URL}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context()
        page = context.new_page()

        # 先导航主站，让主站携带正确的 service= 参数跳转到 isso 登录页
        # isso 登录后会按 service= 自动跳回主站，SPA 才能拿到 ticket 换 token
        page.goto(MAIN_URL)
        # 等待主站重定向到 isso 登录页
        page.wait_for_load_state("networkidle", timeout=15_000)

        print(
            "\n"
            "══════════════════════════════════════════════\n"
            "  浏览器已打开登录页，请完成登录。\n"
            "  登录成功并看到主站页面后，\n"
            "  回到此终端按 Enter 键继续...\n"
            "══════════════════════════════════════════════\n",
            flush=True,
        )
        input()

        logger.info(f"当前 URL: {page.url}")

        # 等待 SPA 处理 ticket 写入 token（若还在 isso 则等跳回主站）
        if "recruitment/internet/main" not in page.url:
            logger.warning("当前仍在登录页，等待跳回主站（最多 30 秒）...")
            try:
                page.wait_for_url(
                    lambda url: "recruitment/internet/main" in url,
                    timeout=30_000,
                )
            except Exception:
                logger.warning("未检测到主站 URL，继续尝试读取 token...")

        page.wait_for_load_state("networkidle", timeout=30_000)
        page.wait_for_timeout(2000)
        logger.info(f"最终 URL: {page.url}")

        # ── 调试：打印 localStorage 和 sessionStorage 全部内容 ──
        storage_dump = page.evaluate("""() => {
            function dump(storage) {
                const out = {};
                for (let i = 0; i < storage.length; i++) {
                    const k = storage.key(i);
                    try { out[k] = JSON.parse(storage.getItem(k)); }
                    catch { out[k] = storage.getItem(k); }
                }
                return out;
            }
            return { local: dump(localStorage), session: dump(sessionStorage) };
        }""")
        import json as _json
        logger.info("=== localStorage ===\n" + _json.dumps(storage_dump["local"], ensure_ascii=False, indent=2)[:3000])
        logger.info("=== sessionStorage ===\n" + _json.dumps(storage_dump["session"], ensure_ascii=False, indent=2)[:2000])

        # 提取 token：在 localStorage 和 sessionStorage 中递归搜索
        def _find_token(obj):
            if isinstance(obj, dict):
                if "token" in obj and isinstance(obj["token"], str) and len(obj["token"]) > 10:
                    return obj["token"]
                for v in obj.values():
                    result = _find_token(v)
                    if result:
                        return result
            return None

        token = _find_token(storage_dump["local"]) or _find_token(storage_dump["session"])

        cookies = context.cookies()
        browser.close()

    for cookie in cookies:
        session.cookies.set(
            name=cookie["name"],
            value=cookie["value"],
            domain=cookie.get("domain", ""),
            path=cookie.get("path", "/"),
        )

    if token:
        session.headers["Authorization"] = f"Bearer {token}"
        logger.info("已从 localStorage 提取 token 并注入 Authorization 头")
    else:
        logger.warning("未能从 localStorage 获取 token，联系电话可能仍为空")


def ensure_logged_in(session: requests.Session) -> None:
    """若未登录则自动弹出浏览器引导登录，登录后再次验证。"""
    logger.info("正在检测登录状态（联系电话权限）...")
    if check_login(session):
        logger.info("已登录，可获取联系电话")
        return

    logger.warning(f"未登录或无联系电话权限，即将打开浏览器引导登录: {MAIN_URL}")
    browser_login(session)

    if check_login(session):
        logger.info("登录验证成功，联系电话可正常获取")
    else:
        logger.warning("登录验证未通过，联系电话可能仍为空（继续抓取其他字段）")


# ──────────────────────────────────────────────────────────────────────
# API 调用
# ──────────────────────────────────────────────────────────────────────

def fetch_position_list(
    session: requests.Session,
    city_code: str,
    page_num: int = 1,
    page_size: int = PAGE_SIZE,
    keyword: Optional[str] = None,
) -> dict:
    """抓取职位列表（分页）"""
    url = f"{BASE_URL}/internet/retrieval/c/recruitment/homepage/positions"
    payload: dict = {
        "current": page_num,   # MyBatis-Plus 分页字段（原 pageNum 被 API 忽略）
        "size": page_size,     # MyBatis-Plus 分页字段（原 pageSize 被 API 忽略）
        "acb204": city_code,
    }
    if keyword:
        payload["bce055"] = keyword

    resp = session.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"列表接口失败: {data.get('msg', '未知错误')}")
    return data["data"]


def fetch_position_detail(session: requests.Session, position_id: str) -> dict:
    """抓取单个职位详情"""
    url = f"{BASE_URL}/internet/r/c/webpage/homepage/position/detail/{position_id}"
    resp = session.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"详情接口失败 [{position_id}]: {data.get('msg', '未知错误')}")
    return data["data"]


# ──────────────────────────────────────────────────────────────────────
# 数据解析
# ──────────────────────────────────────────────────────────────────────

def parse_job(detail: dict, city_name: str = "") -> dict:
    """
    将 API 返回的原始字段映射为可读字段。

    列表接口返回的字段已包含大部分信息；详情接口额外补充:
      - acb22a  岗位描述全文
      - aae004  联系人姓名
      - aae005  联系电话
      - acc530  详细地址
    """
    tags = []
    for field in ("bgb249", "aab022Name", "acb239Name", "aab019Name", "aab056Name"):
        val = detail.get(field)
        if val:
            tags.append(val)

    return {
        "职位ID":     detail.get("bcb009", ""),
        "职位名称":   detail.get("bce055", ""),
        "公司名称":   detail.get("aab004", ""),
        "标签":       " | ".join(tags),
        "薪资":       detail.get("bcca68", ""),
        "其他福利":   detail.get("bcb182Name", "") or "",
        "联系人":     detail.get("aae004", "") or "",
        "联系电话":   detail.get("aae005", "") or "",
        "学历要求":   detail.get("aac011Name", "") or "",
        "工作经验":   detail.get("aae162Name", "") or "",
        "工作城市":   city_name,
        "工作地点":   detail.get("acb204Name", "") or "",
        "详细地址":   detail.get("acc530", "") or "",
        "岗位描述":   (detail.get("acb22a", "") or "").replace("\n", " ").strip(),
        "发布时间":   detail.get("bdb286", "") or "",
        "截止时间":   detail.get("bze321", "") or "",
        "详情URL":    (
            f"https://ggfw.hrss.gd.gov.cn/recruitment/internet/main/"
            f"#/positionDetail?id={detail.get('bcb009', '')}"
        ),
    }


# ──────────────────────────────────────────────────────────────────────
# 核心爬取逻辑
# ──────────────────────────────────────────────────────────────────────

def crawl_city(
    session: requests.Session,
    city_name: str,
    city_code: str,
    keyword: Optional[str] = None,
    fetch_detail: bool = True,
    max_pages: int = MAX_PAGES_PER_CITY,
    request_delay: float = REQUEST_DELAY,
    seen_ids: Optional[set] = None,
) -> list[dict]:
    """爬取某个城市的所有职位"""
    jobs = []
    page = 1
    local_seen: set = set()  # 城市内去重
    skipped = 0

    logger.info(f"开始抓取 [{city_name}] (code={city_code})")

    while page <= max_pages:
        try:
            result = fetch_position_list(session, city_code, page, PAGE_SIZE, keyword)
        except Exception as e:
            logger.error(f"  列表第 {page} 页请求失败: {e}")
            break

        records = result.get("records", [])
        total = result.get("total", 0)
        pages = result.get("pages", 1)

        if not records:
            logger.info(f"  第 {page} 页无数据，停止")
            break

        logger.info(
            f"  第 {page}/{pages} 页 | API总条数={total} API总页数={pages} | 本页原始={len(records)} 条"
        )

        page_added = 0
        page_skipped = 0
        for rec in records:
            position_id = rec.get("bcb009", "")

            # 城市内去重 + 跨城市去重
            if position_id and (position_id in local_seen or (seen_ids is not None and position_id in seen_ids)):
                skipped += 1
                page_skipped += 1
                continue
            if position_id:
                local_seen.add(position_id)
                if seen_ids is not None:
                    seen_ids.add(position_id)

            detail = rec  # 列表接口已包含基础字段

            if fetch_detail and position_id:
                time.sleep(request_delay)
                try:
                    detail = fetch_position_detail(session, position_id)
                except Exception as e:
                    logger.warning(f"    详情请求失败 [{position_id}]: {e}，使用列表数据")

            job = parse_job(detail, city_name)
            jobs.append(job)
            page_added += 1

        logger.info(f"  第 {page} 页处理完：新增 {page_added} 条，跳过重复 {page_skipped} 条")

        # API 返回的 pages 有时不准确，以实际无数据为准；
        # 若 API 明确表示已是最后一页则停止
        if page >= pages:
            logger.info(f"  已到达 API 最后一页 (pages={pages})，停止翻页")
            break

        page += 1
        time.sleep(request_delay)

    logger.info(f"  [{city_name}] 共抓取 {len(jobs)} 条职位（跳过重复 {skipped} 条）")
    return jobs


# ──────────────────────────────────────────────────────────────────────
# 输出
# ──────────────────────────────────────────────────────────────────────

FIELDS = [
    "职位名称", "公司名称", "标签", "薪资", "其他福利",
    "联系人", "联系电话", "学历要求", "工作经验",
    "工作城市", "工作地点", "详细地址", "岗位描述",
    "发布时间", "截止时间", "详情URL", "职位ID",
]


def save_csv(jobs: list[dict], filepath: str) -> None:
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(jobs)
    logger.info(f"已保存 CSV: {filepath} ({len(jobs)} 条)")


def save_json(jobs: list[dict], filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=2)
    logger.info(f"已保存 JSON: {filepath} ({len(jobs)} 条)")


# ──────────────────────────────────────────────────────────────────────
# CLI 入口
# ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="广东公共求职招聘服务平台 职位爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
可用城市:
  {', '.join(CITY_CODES.keys())}

示例:
  # 抓取广州所有职位（含详情）
  python gd_job_spider.py --cities 广州

  # 抓取广州+深圳，关键词筛选，不抓详情（更快）
  python gd_job_spider.py --cities 广州 深圳 --keyword 工程师 --no-detail

  # 抓取所有城市
  python gd_job_spider.py --all-cities

  # 最多抓 3 页（快速测试）
  python gd_job_spider.py --cities 广州 --max-pages 3
        """,
    )
    parser.add_argument(
        "--cities", nargs="+", metavar="城市",
        help="指定城市（可多个），例如: 广州 深圳",
    )
    parser.add_argument(
        "--all-cities", action="store_true",
        help="抓取所有城市",
    )
    parser.add_argument(
        "--keyword", metavar="关键词",
        help="职位名称关键词过滤",
    )
    parser.add_argument(
        "--no-detail", action="store_true",
        help="跳过详情页请求（更快，但缺少岗位描述、联系方式）",
    )
    parser.add_argument(
        "--max-pages", type=int, default=MAX_PAGES_PER_CITY, metavar="N",
        help=f"每个城市最多抓取页数 (默认 {MAX_PAGES_PER_CITY})",
    )
    parser.add_argument(
        "--delay", type=float, default=REQUEST_DELAY, metavar="秒",
        help=f"请求间隔秒数 (默认 {REQUEST_DELAY})",
    )
    parser.add_argument(
        "--output-dir", default=".", metavar="目录",
        help="输出目录 (默认当前目录)",
    )
    parser.add_argument(
        "--format", choices=["csv", "json", "both"], default="both",
        help="输出格式 (默认 both)",
    )
    args = parser.parse_args()

    # 确定目标城市
    if args.all_cities:
        target_cities = CITY_CODES
    elif args.cities:
        target_cities = {}
        for name in args.cities:
            if name not in CITY_CODES:
                parser.error(f"未知城市: {name}，可选: {', '.join(CITY_CODES)}")
            target_cities[name] = CITY_CODES[name]
    else:
        parser.error("请指定 --cities 或 --all-cities")

    request_delay = args.delay
    os.makedirs(args.output_dir, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    # 抓详情时才需要登录（联系电话字段需要登录权限）
    if not args.no_detail:
        ensure_logged_in(session)

    all_jobs: list[dict] = []
    global_seen_ids: set = set()  # 跨城市去重

    for city_name, city_code in target_cities.items():
        city_jobs = crawl_city(
            session,
            city_name=city_name,
            city_code=city_code,
            keyword=args.keyword,
            fetch_detail=not args.no_detail,
            max_pages=args.max_pages,
            request_delay=request_delay,
            seen_ids=global_seen_ids,
        )
        all_jobs.extend(city_jobs)

    if not all_jobs:
        logger.warning("未抓取到任何数据")
        return

    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    city_tag = "_".join(target_cities.keys()) if len(target_cities) <= 3 else "全省"
    base_name = f"gd_jobs_{city_tag}_{timestamp}"

    if args.format in ("csv", "both"):
        save_csv(all_jobs, os.path.join(args.output_dir, f"{base_name}.csv"))
    if args.format in ("json", "both"):
        save_json(all_jobs, os.path.join(args.output_dir, f"{base_name}.json"))

    logger.info(f"全部完成，共 {len(all_jobs)} 条职位数据（已去重，全局唯一职位ID数: {len(global_seen_ids)}）")


if __name__ == "__main__":
    main()
