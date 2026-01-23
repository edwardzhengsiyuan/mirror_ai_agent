# BaZi Engine API Reference

Developer-facing API reference for the BaZi calculation engine. Structured fields use namespaced enum codes (`NAMESPACE:CODE`).

---

## Engine Overview

- `bazi/` is the current engine implementation (formerly `bazi_new`), external import paths remain unchanged
- Structured output enum fields are unified as namespace codes (`NAMESPACE:CODE`); for Chinese display, use `bazi.core.property.strip_ns` + enum mapping
- `BaziChartAnalyseFrame.find_yun_liu_nian_liuyue(target_year)` returns readable annual fortune query text with complete dayun, liunian, liuyue info
- `paipan_tool` extracts `dayun_list` directly from `frame.res["yun"]` (major luck cycle list) for planning prompts

---

## Enum Overview

**Definition Location**
- Unified in `bazi/core/property.py`

**External Return Format (Namespaced Enum Codes)**
- Unified output as: `NAMESPACE:CODE`
  - Example: `GAN:WU` (Heavenly Stem 戊), `ZHI:WU` (Earthly Branch 午), `SHENSHA:TIANYI`
- Common `NAMESPACE`: `YINYANG`, `WUXING`, `GAN`, `ZHI`, `SHISHEN`, `SHENGXIAO`, `SHENSHA`, `NAYIN`, `DISHI`, `SHENQIANGRUO`, `GEJU`, `GAN_RELATION_TYPE`, `ZHI_RELATION_TYPE`, `ZODIAC_COMPAT_RELATION`, `ZODIAC_COMPAT_FAVORABILITY`, `ZODIAC_COMPAT_DETAIL`

**Basic Enums**
- `Yinyang`: `YIN`, `YANG`
- `Wuxing`: `MU` (Wood), `HUO` (Fire), `TU` (Earth), `JIN` (Metal), `SHUI` (Water)
- `Gan`: `JIA`, `YI`, `BING`, `DING`, `WU`, `JI`, `GENG`, `XIN`, `REN`, `GUI`
- `Zhi`: `ZI`, `CHOU`, `YIN`, `MAO`, `CHEN`, `SI`, `WU`, `WEI`, `SHEN`, `YOU`, `XU`, `HAI`
- `Shishen`: `RIZHU`, `BIJIAN`, `JIECAI`, `SHISHEN`, `SHANGGUAN`, `PIANCAI`, `ZHENGCAI`, `QISHA`, `ZHENGGUAN`, `PIANYIN`, `ZHENGYIN`
- `Shengxiao`: `SHU` (Rat), `NIU` (Ox), `HU` (Tiger), `TU` (Rabbit), `LONG` (Dragon), `SHE` (Snake), `MA` (Horse), `YANG` (Goat), `HOU` (Monkey), `JI` (Rooster), `GOU` (Dog), `ZHU` (Pig)

**Zodiac Compatibility Enums**
- `ZodiacCompatibilityRelation`: `SAME`, `LIUHE`, `SANHE`, `LIUCHONG`, `LIUHAI`, `NEUTRAL`
- `ZodiacCompatibilityFavorability`: `FAVORABLE`, `UNFAVORABLE`, `NEUTRAL`
- `ZodiacCompatibilityDetail`: `SAME`, `LIUHE`, `SANHE`, `LIUCHONG`, `LIUHAI`, `NEUTRAL`

**Shensha (Spirit Influences) Enum**
- `ShenshaEnum`: `GUCHEN`, `GUASU`, `HONGLUAN`, `TIANXI`, `TIANDEGUIREN`, `YUEDE`, `TIANYI`, `WENCHANG`, `YANGREN`, `LUSHEN`, `HONGYAN`, `JIANGXING`, `HUAGAI`, `YIMA`, `JIESHA`, `WANGSHEN`, `TAOHUA`, `TAIJIGUIREN`, `KONGWANG`, `SANQIGUIREN`, `FUXINGGUIREN`, `KUIGANG`, `GUOYINGUIREN`, `DEXIUGUIREN`, `XUETANG`, `CIGUAN`, `TIANCHUGUIREN`, `JINYU`, `ZAISHA`, `BAZHUAN`, `TONGZI`, `YINCHAYANCUO`, `SHIEDABAI`, `TIANYII`

**Nayin / DiShi**
- `Nayin`: `HAI_ZHONG_JIN`, `LU_ZHONG_HUO`, `DA_LIN_MU`, `LU_PANG_TU`, `JIAN_FENG_JIN`, `SHAN_TOU_HUO`, `JIAN_XIA_SHUI`, `CHENG_TOU_TU`, `BAI_LA_JIN`, `YANG_LIU_MU`, `QUAN_ZHONG_SHUI`, `WU_SHANG_TU`, `PI_LI_HUO`, `SONG_BAI_MU`, `CHANG_LIU_SHUI`, `SHA_ZHONG_JIN`, `SHAN_XIA_HUO`, `PING_DI_MU`, `BI_SHANG_TU`, `JIN_BO_JIN`, `FO_DENG_HUO`, `TIAN_HE_SHUI`, `DA_YI_TU`, `CHAI_CHUAN_JIN`, `SANG_ZHE_MU`, `DA_XI_SHUI`, `SHA_ZHONG_TU`, `TIAN_SHANG_HUO`, `SHI_LIU_MU`, `DA_HAI_SHUI`
- `DiShi`: `CHANGSHENG`, `MUYU`, `GUANDAI`, `LINGUAN`, `DIWANG`, `SHUAI`, `BING`, `SI`, `MU`, `JUE`, `TAI`, `YANG`

**Body Strength**
- `ShenQiangRuo`: `QIANG` (Strong), `ZHONGHE` (Balanced), `RUO` (Weak)

**Relation Types (type field in structured relation objects)**
- `GanRelationType`: `WUHE`
- `ZhiRelationType`: `SANHUI`, `SANHE`, `BANHE`, `GONGHE`, `SANXING`, `XING`, `ZIXING`, `LIUHE`, `LIUCHONG`, `LIUHAI`, `XIANGPO`

**Chart Pattern (Geju)**
- `GejuEnum`: `NEED_MORE_ANALYSIS`, `ZHUANWANG_GE`, `YANGREN_GE`, `LUSHEN_GE`, `BIJIAN_GE`, `JIECAI_GE`, `SHISHEN_GE`, `SHANGGUAN_GE`, `PIANCAI_GE`, `ZHENGCAI_GE`, `QISHA_GE`, `ZHENGGUAN_GE`, `PIANYIN_GE`, `ZHENGYIN_GE`

---

## Compatibility Analysis

**Entry Method**
- `BaziChartAnalyseFrame.get_compatibility_analysis(other_chart)` in `bazi/main/bazi_chart_analyse_frame.py`

**Input**
- `self`: Initialized `BaziChartAnalyseFrame` (Chart A)
- `other_chart`: `BaziChart` (Chart B)

**Notes**
- `BaziChart` is built with `BaziChart(lunar, gender, without_time)`
- `get_compatibility_analysis` internally calculates shensha interactions, zodiac compatibility, and five element vector matching

**Output**
```json
{
  "a_wang_b": ["SHENSHA:GUCHEN", "..."],
  "b_wang_a": ["SHENSHA:TAOHUA", "..."],
  "shengxiao_hehun": {
    "a_shengxiao": "SHENGXIAO:SHU",
    "b_shengxiao": "SHENGXIAO:NIU",
    "a_nianzhi": "ZHI:ZI",
    "b_nianzhi": "ZHI:CHOU",
    "relation": "ZODIAC_COMPAT_RELATION:LIUHE",
    "favorable": "ZODIAC_COMPAT_FAVORABILITY:FAVORABLE",
    "detail": "ZODIAC_COMPAT_DETAIL:LIUHE"
  },
  "wuxing_vector": {
    "xiangsi_du": 0.0,
    "hubu_du": 0.0
  }
}
```

**Field Descriptions**
- `a_wang_b`: Shensha enums from Chart A matching Chart B's rules (deduplicated, sorted)
- `b_wang_a`: Shensha enums from Chart B matching Chart A's rules (deduplicated, sorted)
- `shengxiao_hehun`: Zodiac compatibility (year branch)
- `wuxing_vector`: Five element vector similarity and complementarity, range 0-100

---

## Basic Chart Result

**Entry Method**
- `BaziChartAnalyseFrame.generate_basic_res()` in `bazi/main/bazi_chart_analyse_frame.py` (called automatically during initialization)
- Results stored in `BaziChartAnalyseFrame.res`

**Input**
- `lunar`: `lunar_python` Lunar object
- `gender`: `"male"` or `"female"`
- `without_time`: `bool`, if `True` then no hour pillar

**Output**
```json
{
  "zhu_list": {
    "year_zhu": {"gan": {"name": "GAN:JIA", "wuxing": "WUXING:MU", "yinyang": "YINYANG:YANG", "shishen": "SHISHEN:BIJIAN"}, "zhi": {"name": "ZHI:ZI", "wuxing": "WUXING:SHUI", "yinyang": "YINYANG:YANG", "hidden_gans": [...]}},
    "month_zhu": {...},
    "day_zhu": {...},
    "hour_zhu": {...},
    "taiyuan_zhu": {...},
    "minggong_zhu": {...},
    "shengong_zhu": {...}
  },
  "nayin": ["NAYIN:HAI_ZHONG_JIN", "..."],
  "daygan_dishi": ["DISHI:CHANGSHENG", "..."],
  "zizuo_dishi": ["DISHI:MUYU", "..."],
  "xunkong": [["ZHI:ZI","ZHI:CHOU"], [...]],
  "startyun": [0, 0, 0, 0],
  "shensha": [{"values": ["SHENSHA:GUCHEN", "..."]}],
  "yun": [...],
  "wuxing_proportions": {"WUXING:MU": 0.0, ...},
  "shishen_proportions": {"SHISHEN:BIJIAN": 0.0, ...},
  "shenqiangshenruo": "SHENQIANGRUO:ZHONGHE",
  "rizhu": {"name": "GAN:BING", ...},
  "shengxiao": "SHENGXIAO:SHU",
  "geju": ["GEJU:NEED_MORE_ANALYSIS"]
}
```

**Field Descriptions**
- `zhu_list`: Year/month/day/hour, taiyuan/minggong/shengong pillar info; no `hour_zhu` when `without_time=True`
- `nayin`: `NAYIN:<Nayin.name>` list
- `daygan_dishi`: `DISHI:<DiShi.name>` list
- `zizuo_dishi`: `DISHI:<DiShi.name>` list
- `xunkong`: Void pillars list, each item is two branch enum codes array like `["ZHI:ZI","ZHI:CHOU"]`
- `shensha`: `SHENSHA:<ShenshaEnum.value>` list
- `yun`: Major luck/annual/monthly fortune structure; enum fields are `NAMESPACE:CODE`; `gan_relation`/`zhi_relation` are structured relation object lists
- `wuxing_proportions`: key is `WUXING:<Wuxing.name>`
- `shishen_proportions`: key is `SHISHEN:<Shishen.name>`
- `shenqiangshenruo`: `SHENQIANGRUO:<ShenQiangRuo.name>` (`QIANG`/`ZHONGHE`/`RUO`)
- `shengxiao`: `SHENGXIAO:<Shengxiao.name>`
- `geju`: `GEJU:<GejuEnum.name>` list

---

## Basic Chart Result (Without Major Luck)

**Entry Method**
- `BaziChartAnalyseFrame.generate_basic_res_without_yun()`

**Output**
- Same as basic chart result but without `yun` field

---

## Analysis Summary Text

**Entry Method**
- `BaziChartAnalyseFrame.get_analysis_summary()`

**Output**
```json
{
  "ans": "Main log output content",
  "liupan": "Annual fortune/major luck text",
  "guji": "Classical reference text"
}
```

---

## Annual Fortune Query (Locate Specific Year)

**Entry Method**
- `BaziChartAnalyseFrame.find_yun_liu_nian_liuyue(target_year)`

**Output**
- If found: returns text string (for display)
- If not found: returns `null`

---

## Shensha Query (Specific Date)

**Entry Method**
- `BaziChartAnalyseFrame.query_shensha_for_datetime(year, month, day, hour=None)`

**Output**
```json
{
  "date": "YYYY-MM-DD HH:00",
  "bazi": {
    "year": {"gan": "GAN:JIA", "zhi": "ZHI:ZI"},
    "month": {"gan": "GAN:YI", "zhi": "ZHI:CHOU"},
    "day": {"gan": "GAN:BING", "zhi": "ZHI:YIN"},
    "hour": {"gan": "GAN:DING", "zhi": "ZHI:MAO"}
  },
  "shensha": {"year": [], "month": [], "day": [], "hour": []}
}
```
Note: Items in `shensha` lists are `SHENSHA:<ShenshaEnum.value>`.

---

## Shensha Impact Query (Specific Date)

**Entry Method**
- `BaziChartAnalyseFrame.query_shensha_impact_for_datetime(year, month, day, hour=None)`

**Output**
```json
{
  "date": "YYYY-MM-DD HH:00",
  "bazi": {...},
  "shensha": {"year": [], "month": [], "day": [], "hour": []},
  "impact": {
    "year": [{"name": "SHENSHA:GUCHEN", "impact": {"career": 0, "love": 0, "study": 0, "health": 0, "life": 0, "spirituality": 0, "interpersonal": 0, "overall": 0}}],
    "month": [],
    "day": [],
    "hour": []
  }
}
```
Note: `shensha` and `impact[*].name` are both `SHENSHA:<ShenshaEnum.value>`.
