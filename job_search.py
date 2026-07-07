"""普工招聘信息查询模块。

提供两个核心能力:
  1. search_jobs() —— 按条件筛选岗位,返回格式化文本
  2. (可选)独立命令行运行: python job_search.py --city 东莞 --salary 5000-8000

数据来源:内置模拟数据集(覆盖主流用工城市)。可替换为真实 API / 爬虫。
"""

import re
import argparse

# ============================================================
# 模拟数据集:覆盖珠三角、长三角、京津冀等主要用工地区
# 每条记录: (职位名, 公司, 城市, 区/镇, 月薪下限, 月薪上限, 是否包吃住, 学历要求, 经验要求, 标签)
# ============================================================
_JOBS = [
    # ---- 东莞 ----
    ("电子厂普工", "东莞华贝电子", "东莞", "松山湖", 5000, 6500, True, "不限", "不限", "包吃住,坐班,两班倒"),
    ("组装普工", "东莞富强电子", "东莞", "长安镇", 4800, 6200, True, "不限", "不限", "包吃住,长白班"),
    ("包装工", "东莞雀巢美极", "东莞", "茶山镇", 4500, 5800, True, "不限", "不限", "包吃住,空调车间"),
    ("注塑普工", "东莞联丰科艺", "东莞", "大朗镇", 5200, 6800, True, "不限", "不限", "包吃住,夜班补贴"),
    ("SMT操作员", "东莞长城开发", "东莞", "虎门镇", 5500, 7000, False, "初中", "不限", "坐班,两班倒,五险"),
    ("品质检验员", "东莞立讯精密", "东莞", "清溪镇", 5000, 6500, True, "初中", "1年", "包吃住,长白班,坐班"),
    ("CNC操作工", "东莞捷荣技术", "东莞", "长安镇", 6000, 8000, True, "不限", "不限", "包吃住,两班倒"),
    ("搬运工", "东莞徐福记", "东莞", "东城区", 4800, 6000, True, "不限", "不限", "包吃住,体力活"),
    ("普工/操作工", "东莞新能源科技", "东莞", "松山湖", 5500, 7000, True, "初中", "不限", "包吃住,恒温车间,五险一金"),
    ("装配工", "东莞歌尔股份", "东莞", "松山湖", 5200, 6800, True, "不限", "不限", "包吃住,坐班,长白班"),

    # ---- 深圳 ----
    ("普工", "深圳比亚迪", "深圳", "坪山区", 5500, 7500, True, "不限", "不限", "包吃住,五险一金,大厂"),
    ("电子装配工", "深圳富士康", "深圳", "龙华区", 5000, 7000, True, "不限", "不限", "包吃住,两班倒,坐班"),
    ("仓库理货员", "深圳京东物流", "深圳", "宝安区", 6000, 8000, False, "初中", "不限", "五险一金,长白班"),
    ("SMT普工", "深圳传音控股", "深圳", "南山区", 5500, 7000, False, "初中", "不限", "坐班,五险"),
    ("质检员", "深圳华为终端", "深圳", "松岗", 6000, 8000, True, "高中", "1年", "包吃住,五险一金,加班稳定"),

    # ---- 广州 ----
    ("流水线普工", "广州视源股份", "广州", "黄埔区", 4800, 6200, True, "不限", "不限", "包吃住,坐班,长白班"),
    ("包装工", "广州宝洁", "广州", "黄埔区", 5000, 6500, True, "初中", "不限", "包吃住,五险一金"),
    ("食品生产工", "广州益力多", "广州", "黄埔区", 4500, 5800, True, "不限", "不限", "包吃住,长白班,恒温车间"),
    ("仓库拣货员", "广州名创优品", "广州", "花都区", 5500, 7500, True, "不限", "不限", "包吃住,多劳多得"),
    ("注塑工", "广州金发科技", "广州", "白云区", 5200, 6800, True, "不限", "不限", "包吃住,两班倒"),

    # ---- 苏州 ----
    ("电子厂普工", "苏州华硕电脑", "苏州", "虎丘区", 5000, 6500, True, "不限", "不限", "包吃住,坐班,两班倒"),
    ("组装工", "苏州博世汽车", "苏州", "工业园区", 5500, 7000, True, "初中", "不限", "包吃住,五险一金"),
    ("SMT操作员", "苏州长城开发", "苏州", "吴江区", 5200, 6800, True, "初中", "不限", "包吃住,恒温车间"),
    ("品质检验", "苏州华兴源创", "苏州", "工业园区", 5500, 7200, True, "高中", "1年", "包吃住,五险一金,长白班"),
    ("CNC操作工", "苏州胜利精密", "苏州", "相城区", 6000, 8000, True, "不限", "不限", "包吃住,两班倒,夜班补贴"),

    # ---- 上海 ----
    ("流水线普工", "上海昌硕科技", "上海", "浦东新区", 5000, 6500, True, "不限", "不限", "包吃住,坐班"),
    ("仓库管理员", "上海菜鸟物流", "上海", "青浦区", 6000, 8000, False, "初中", "不限", "五险一金,长白班"),
    ("食品包装工", "上海光明乳业", "上海", "闵行区", 4800, 6000, True, "不限", "不限", "包吃住,长白班"),
    ("电子普工", "上海英华达", "上海", "闵行区", 5000, 6800, True, "不限", "不限", "包吃住,两班倒,坐班"),
    ("质检员", "上海联合电子", "上海", "嘉定区", 5500, 7200, True, "高中", "1年", "包吃住,五险一金"),

    # ---- 成都 ----
    ("电子厂普工", "成都捷普科技", "成都", "崇州市", 4500, 6000, True, "不限", "不限", "包吃住,坐班"),
    ("操作工", "成都京东方", "成都", "郫都区", 4800, 6500, True, "初中", "不限", "包吃住,五险一金,恒温车间"),
    ("物流分拣员", "成都顺丰速运", "成都", "双流区", 4500, 5800, False, "不限", "不限", "长白班,五险"),
    ("注塑普工", "成都航天模塑", "成都", "龙泉驿区", 4800, 6200, True, "不限", "不限", "包吃住,两班倒"),
    ("食品生产工", "成都新希望", "成都", "新津区", 4000, 5500, True, "不限", "不限", "包吃住,长白班"),

    # ---- 武汉 ----
    ("电子普工", "武汉联想产业基地", "武汉", "东湖高新区", 4500, 6000, True, "不限", "不限", "包吃住,坐班,两班倒"),
    ("质检员", "武汉华星光电", "武汉", "东湖高新区", 4800, 6500, True, "初中", "不限", "包吃住,五险一金"),
    ("汽配普工", "武汉东风零部件", "武汉", "蔡甸区", 5000, 6500, True, "不限", "不限", "包吃住,长白班"),
    ("包装工", "武汉良品铺子", "武汉", "东西湖区", 4200, 5500, True, "不限", "不限", "包吃住,恒温车间"),
    ("SMT操作员", "武汉烽火通信", "武汉", "江夏区", 4800, 6200, True, "初中", "不限", "包吃住,坐班"),
]

# 城市列表(去重)
_CITIES = sorted(set(j[2] for j in _JOBS))


def search_jobs(
    city: str = "",
    salary_min: int = 0,
    salary_max: int = 99999,
    keywords: str = "",
    food_accommodation: bool = False,
    require_food_accom: bool = False,  # 是否严格要求包吃住
    max_results: int = 20,
) -> str:
    """按条件搜索普工岗位,返回格式化文本(供 agent 或命令行使用)。

    Args:
        city:      城市名(如"东莞"),留空表示不限城市
        salary_min: 最低月薪
        salary_max: 最高月薪
        keywords:  关键词(如"坐班""长白班"),空格分隔多个词
        food_accommodation: 如果为 True,优先展示包吃住的岗位
        require_food_accom: 如果为 True,只展示包吃住的岗位
        max_results:最多返回多少条

    Returns:
        格式化的字符串,含统计信息和岗位列表
    """
    results = []

    for job in _JOBS:
        title, company, jcity, district, smin, smax, has_food, edu, exp, tags = job

        # ---- 筛选 ----
        if city and city not in jcity and jcity not in city:
            continue
        if smax < salary_min or smin > salary_max:
            continue
        if require_food_accom and not has_food:
            continue

        # 关键词匹配(职位名 + 公司 + 标签)
        if keywords:
            kw_list = [kw.strip() for kw in keywords.split() if kw.strip()]
            if kw_list:
                search_text = f"{title} {company} {tags}".lower()
                if not all(kw.lower() in search_text for kw in kw_list):
                    continue

        results.append(job)

    # ---- 排序 ----
    # 1)包吃住优先(如果指定了 food_accommodation)
    # 2)按薪资(上限)从高到低
    if food_accommodation or require_food_accom:
        results.sort(key=lambda j: (1 if j[6] else 0, j[5]), reverse=True)
    else:
        results.sort(key=lambda j: j[5], reverse=True)

    # ---- 截断 ----
    results = results[:max_results]

    # ---- 格式化输出 ----
    if not results:
        base = f"在「{city}」" if city else "全国"
        salary_range = f"{salary_min}-{salary_max}元"
        extra = "包吃住 " if require_food_accom else ""
        return f"😔 {base}{extra}未找到匹配「{salary_range}」的普工岗位。试试放宽条件。"

    lines = []
    lines.append(f"✅ 找到 {len(results)} 个岗位{' (优先展示包吃住)' if food_accommodation or require_food_accom else ''}:\n")
    lines.append(f"   {'序号':<4} {'职位':<12} {'公司':<16} {'地区':<10} {'薪资':<10} {'包吃住':<6} {'标签'}")
    lines.append("   " + "-" * 80)

    for i, job in enumerate(results, 1):
        title, company, jcity, district, smin, smax, has_food, edu, exp, tags = job
        salary_str = f"{smin}-{smax}"
        food_str = "✅" if has_food else "❌"
        # 截断过长的字段
        short_title = title[:10]
        short_company = company[:14]
        short_area = f"{jcity}{district[:4]}" if district else jcity
        short_tags = tags[:20]
        lines.append(f"   {i:<4} {short_title:<12} {short_company:<16} {short_area:<10} {salary_str:<10} {food_str:<6} {short_tags}")

    lines.append("")
    lines.append("💡 提示:可进一步筛选 关键词(如长白班/坐班) 或 要求包吃住。")
    return "\n".join(lines)


def _run_cli():
    """命令行入口: python job_search.py --city 东莞 --salary 5000-8000"""
    parser = argparse.ArgumentParser(description="🔧 普工岗位搜索工具")
    parser.add_argument("--city", default="", help="城市名,如 东莞/深圳/苏州,留空不限")
    parser.add_argument("--salary", default="", help="薪资范围,如 5000-8000")
    parser.add_argument("--keywords", default="", help="关键词,如 坐班 长白班,空格分隔")
    parser.add_argument("--food", action="store_true", help="优先展示包吃住的岗位")
    parser.add_argument("--only-food", action="store_true", help="只看包吃住的岗位")
    parser.add_argument("--max", type=int, default=20, help="最多显示多少条(默认20)")

    args = parser.parse_args()

    salary_min, salary_max = 0, 99999
    if args.salary:
        parts = re.split(r"[-–至]", args.salary)
        try:
            salary_min = int(parts[0]) if parts[0] else 0
            salary_max = int(parts[1]) if len(parts) > 1 and parts[1] else 99999
        except ValueError:
            pass

    result = search_jobs(
        city=args.city,
        salary_min=salary_min,
        salary_max=salary_max,
        keywords=args.keywords,
        food_accommodation=args.food or args.only_food,
        require_food_accom=args.only_food,
        max_results=args.max,
    )
    print(result)


if __name__ == "__main__":
    _run_cli()
