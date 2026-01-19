# API 文档 / API Reference (Developer)

EN: This is the developer-facing API reference for the current engine (formerly `bazi_new`). Structured fields use namespaced enum codes (`NAMESPACE:CODE`). The detailed sections below remain in Chinese; English summaries will be expanded as needed.

本文档记录当前已暴露的 API 输入输出，先从合盘开始。**所有返回值中的“可枚举语义字段”均返回枚举码（非中文描述）**，便于多语言映射；数值与日期等字段保持原样。

## 枚举总览（本项目统一输出的 enum 值）

**定义位置**
- 统一在 `bazi/core/property.py`

**对外返回格式（命名空间枚举码）**
- 统一输出为：`NAMESPACE:CODE`
  - 例：`GAN:WU`（天干戊）、`ZHI:WU`（地支午）、`SHENSHA:TIANYI`
- 常用 `NAMESPACE`：`YINYANG`、`WUXING`、`GAN`、`ZHI`、`SHISHEN`、`SHENGXIAO`、`SHENSHA`、`NAYIN`、`DISHI`、`SHENQIANGRUO`、`GEJU`、`GAN_RELATION_TYPE`、`ZHI_RELATION_TYPE`、`ZODIAC_COMPAT_RELATION`、`ZODIAC_COMPAT_FAVORABILITY`、`ZODIAC_COMPAT_DETAIL`

**基础枚举**
- `Yinyang`: `YIN`, `YANG`
- `Wuxing`: `MU`, `HUO`, `TU`, `JIN`, `SHUI`
- `Gan`: `JIA`, `YI`, `BING`, `DING`, `WU`, `JI`, `GENG`, `XIN`, `REN`, `GUI`
- `Zhi`: `ZI`, `CHOU`, `YIN`, `MAO`, `CHEN`, `SI`, `WU`, `WEI`, `SHEN`, `YOU`, `XU`, `HAI`
- `Shishen`: `RIZHU`, `BIJIAN`, `JIECAI`, `SHISHEN`, `SHANGGUAN`, `PIANCAI`, `ZHENGCAI`, `QISHA`, `ZHENGGUAN`, `PIANYIN`, `ZHENGYIN`
- `Shengxiao`: `SHU`, `NIU`, `HU`, `TU`, `LONG`, `SHE`, `MA`, `YANG`, `HOU`, `JI`, `GOU`, `ZHU`

**生肖合婚枚举**
- `ZodiacCompatibilityRelation`: `SAME`, `LIUHE`, `SANHE`, `LIUCHONG`, `LIUHAI`, `NEUTRAL`
- `ZodiacCompatibilityFavorability`: `FAVORABLE`, `UNFAVORABLE`, `NEUTRAL`
- `ZodiacCompatibilityDetail`: `SAME`, `LIUHE`, `SANHE`, `LIUCHONG`, `LIUHAI`, `NEUTRAL`

**神煞枚举**
- `ShenshaEnum`:
  - `GUCHEN`, `GUASU`, `HONGLUAN`, `TIANXI`, `TIANDEGUIREN`, `YUEDE`, `TIANYI`, `WENCHANG`, `YANGREN`, `LUSHEN`, `HONGYAN`, `JIANGXING`, `HUAGAI`, `YIMA`, `JIESHA`, `WANGSHEN`, `TAOHUA`, `TAIJIGUIREN`, `KONGWANG`, `SANQIGUIREN`, `FUXINGGUIREN`, `KUIGANG`, `GUOYINGUIREN`, `DEXIUGUIREN`, `XUETANG`, `CIGUAN`, `TIANCHUGUIREN`, `JINYU`, `ZAISHA`, `BAZHUAN`, `TONGZI`, `YINCHAYANCUO`, `SHIEDABAI`, `TIANYII`

**纳音 / 地势**
- `Nayin`:
  - `HAI_ZHONG_JIN`, `LU_ZHONG_HUO`, `DA_LIN_MU`, `LU_PANG_TU`, `JIAN_FENG_JIN`, `SHAN_TOU_HUO`, `JIAN_XIA_SHUI`, `CHENG_TOU_TU`, `BAI_LA_JIN`, `YANG_LIU_MU`, `QUAN_ZHONG_SHUI`, `WU_SHANG_TU`, `PI_LI_HUO`, `SONG_BAI_MU`, `CHANG_LIU_SHUI`, `SHA_ZHONG_JIN`, `SHAN_XIA_HUO`, `PING_DI_MU`, `BI_SHANG_TU`, `JIN_BO_JIN`, `FO_DENG_HUO`, `TIAN_HE_SHUI`, `DA_YI_TU`, `CHAI_CHUAN_JIN`, `SANG_ZHE_MU`, `DA_XI_SHUI`, `SHA_ZHONG_TU`, `TIAN_SHANG_HUO`, `SHI_LIU_MU`, `DA_HAI_SHUI`
- `DiShi`:
  - `CHANGSHENG`, `MUYU`, `GUANDAI`, `LINGUAN`, `DIWANG`, `SHUAI`, `BING`, `SI`, `MU`, `JUE`, `TAI`, `YANG`

**身强身弱**
- `ShenQiangRuo`: `QIANG`, `ZHONGHE`, `RUO`

**关系类型（结构化关系对象的 type 字段）**
- `GanRelationType`: `WUHE`
- `ZhiRelationType`: `SANHUI`, `SANHE`, `BANHE`, `GONGHE`, `SANXING`, `XING`, `ZIXING`, `LIUHE`, `LIUCHONG`, `LIUHAI`, `XIANGPO`

**格局**
- `GejuEnum`:
  - `NEED_MORE_ANALYSIS`, `ZHUANWANG_GE`, `YANGREN_GE`, `LUSHEN_GE`
  - `BIJIAN_GE`, `JIECAI_GE`, `SHISHEN_GE`, `SHANGGUAN_GE`, `PIANCAI_GE`, `ZHENGCAI_GE`, `QISHA_GE`, `ZHENGGUAN_GE`, `PIANYIN_GE`, `ZHENGYIN_GE`

## 合盘（Compatibility）

**入口方法**
- `bazi/main/bazi_chart_analyse_frame.py` 中的 `BaziChartAnalyseFrame.get_compatibility_analysis(other_chart)`

**输入**
- `self`: 已初始化的 `BaziChartAnalyseFrame`（命盘 A）
- `other_chart`: `BaziChart`（命盘 B）

**说明**
- `BaziChart` 由 `BaziChart(lunar, gender, without_time)` 构建。
- `get_compatibility_analysis` 内部会计算神煞互涉、生肖合婚、五行向量匹配度。

**输出**
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

**字段说明**
- `a_wang_b`: 命盘 A 中满足命盘 B 神煞规则的神煞枚举列表（去重、排序）
- `b_wang_a`: 命盘 B 中满足命盘 A 神煞规则的神煞枚举列表（去重、排序）
- `shengxiao_hehun`: 生肖合婚（年支）
- `wuxing_vector`: 五行向量相似度与互补度，范围 0-100

**枚举值**
- 见本文档顶部“枚举总览”

## 基础排盘结果（Basic Result）

**入口方法**
- `bazi/main/bazi_chart_analyse_frame.py` 中的 `BaziChartAnalyseFrame.generate_basic_res()`（初始化时自动调用）
- 结果保存于 `BaziChartAnalyseFrame.res`

**输入**
- `lunar`: `lunar_python` 的 Lunar 对象
- `gender`: `"male"` 或 `"female"`
- `without_time`: `bool`，为 `True` 时不含时柱

**输出**
```json
{
  "zhu_list": {
    "year_zhu": {"gan": {"name": "GAN:JIA", "wuxing": "WUXING:MU", "yinyang": "YINYANG:YANG", "shishen": "SHISHEN:BIJIAN"}, "zhi": {"name": "ZHI:ZI", "wuxing": "WUXING:SHUI", "yinyang": "YINYANG:YANG", "hidden_gans": [{"name":"GAN:GUI","wuxing":"WUXING:SHUI","yinyang":"YINYANG:YIN","shishen":"SHISHEN:ZHENGYIN"}]}},
    "month_zhu": {"gan": {...}, "zhi": {...}},
    "day_zhu": {"gan": {...}, "zhi": {...}},
    "hour_zhu": {"gan": {...}, "zhi": {...}},
    "taiyuan_zhu": {"gan": {...}, "zhi": {...}},
    "minggong_zhu": {"gan": {...}, "zhi": {...}},
    "shengong_zhu": {"gan": {...}, "zhi": {...}}
  },
  "nayin": ["NAYIN:HAI_ZHONG_JIN", "..."],
  "daygan_dishi": ["DISHI:CHANGSHENG", "..."],
  "zizuo_dishi": ["DISHI:MUYU", "..."],
  "xunkong": [["ZHI:ZI","ZHI:CHOU"], ["...","..."]],
  "startyun": [0, 0, 0, 0],
  "shensha": [{"values": ["SHENSHA:GUCHEN", "..."]}],
  "yun": [
    {
      "age": 0,
      "year": 0,
      "gan": "GAN:JIA",
      "zhi": "ZHI:ZI",
      "gan_wuxing": "WUXING:MU",
      "zhi_wuxing": "WUXING:SHUI",
      "gan_shishen": "SHISHEN:BIJIAN",
      "zhi_shishen": "SHISHEN:ZHENGYIN",
      "gan_relation": [{"type": "GAN_RELATION_TYPE:WUHE", "members": ["GAN:JIA", "GAN:JI"]}],
      "zhi_relation": [{"type": "ZHI_RELATION_TYPE:LIUHE", "members": ["ZHI:ZI", "ZHI:CHOU"]}],
      "shensha": ["SHENSHA:GUCHEN", "..."],
      "liunian": [
        {
          "age": 0,
          "year": 0,
          "gan": "GAN:YI",
          "zhi": "ZHI:CHOU",
          "gan_wuxing": "WUXING:MU",
          "zhi_wuxing": "WUXING:TU",
          "gan_shishen": "SHISHEN:JIECAI",
          "zhi_shishen": "SHISHEN:SHISHEN",
          "gan_relation": [{"type": "GAN_RELATION_TYPE:WUHE", "members": ["GAN:YI", "GAN:GENG"]}],
          "zhi_relation": [{"type": "ZHI_RELATION_TYPE:LIUCHONG", "members": ["ZHI:ZI", "ZHI:WU"]}],
          "shensha": ["SHENSHA:GUCHEN", "..."],
          "liuyue": [
            {
              "month": 0,
              "day": 0,
              "gan": "GAN:BING",
              "zhi": "ZHI:YIN",
              "gan_wuxing": "WUXING:HUO",
              "zhi_wuxing": "WUXING:MU",
              "gan_shishen": "SHISHEN:SHISHEN",
              "zhi_shishen": "SHISHEN:BIJIAN",
              "gan_relation": [{"type": "GAN_RELATION_TYPE:WUHE", "members": ["GAN:BING", "GAN:XIN"]}],
              "zhi_relation": [{"type": "ZHI_RELATION_TYPE:SANHE", "members": ["ZHI:SHEN", "ZHI:ZI", "ZHI:CHEN"]}]
            }
          ]
        }
      ]
    }
  ],
  "wuxing_proportions": {"WUXING:MU": 0.0, "WUXING:HUO": 0.0, "WUXING:TU": 0.0, "WUXING:JIN": 0.0, "WUXING:SHUI": 0.0},
  "shishen_proportions": {"SHISHEN:BIJIAN": 0.0, "...": 0.0},
  "shenqiangshenruo": "SHENQIANGRUO:ZHONGHE",
  "rizhu": {"name": "GAN:BING", "wuxing": "WUXING:HUO", "yinyang": "YINYANG:YANG", "shishen": "SHISHEN:RIZHU"},
  "shengxiao": "SHENGXIAO:SHU",
  "geju": ["GEJU:NEED_MORE_ANALYSIS"]
}
```

**字段说明**
- `zhu_list`: 年/月/日/时、胎元/命宫/身宫柱信息；`without_time=True` 时无 `hour_zhu`
- `zhu_list.*.gan.name`: `GAN:<Gan.name>`（如 `GAN:JIA`）
- `zhu_list.*.gan.wuxing`: `WUXING:<Wuxing.name>`
- `zhu_list.*.gan.yinyang`: `YINYANG:<Yinyang.name>`
- `zhu_list.*.gan.shishen`: `SHISHEN:<Shishen.name>`
- `zhu_list.*.zhi.name`: `ZHI:<Zhi.name>`（如 `ZHI:ZI`）
- `zhu_list.*.zhi.wuxing`: `WUXING:<Wuxing.name>`
- `zhu_list.*.zhi.yinyang`: `YINYANG:<Yinyang.name>`
- `zhu_list.*.zhi.hidden_gans[*].name`: `GAN:<Gan.name>`
- `zhu_list.*.zhi.hidden_gans[*].wuxing`: `WUXING:<Wuxing.name>`
- `zhu_list.*.zhi.hidden_gans[*].yinyang`: `YINYANG:<Yinyang.name>`
- `zhu_list.*.zhi.hidden_gans[*].shishen`: `SHISHEN:<Shishen.name>`
- `nayin`: `NAYIN:<Nayin.name>` 列表
- `daygan_dishi`: `DISHI:<DiShi.name>` 列表
- `zizuo_dishi`: `DISHI:<DiShi.name>` 列表
- `xunkong`: 旬空列表，每项为两个地支枚举码组成的数组，如 `["ZHI:ZI","ZHI:CHOU"]`
- `shensha`: `SHENSHA:<ShenshaEnum.value>` 列表
- `yun`: 大运/流年/流月结构；相关枚举字段均为 `NAMESPACE:CODE`；`gan_relation`/`zhi_relation` 为结构化关系对象列表\n+- `gan_relation[*].type`: `GAN_RELATION_TYPE:<GanRelationType.name>`\n+- `gan_relation[*].members[*]`: `GAN:<Gan.name>`\n+- `zhi_relation[*].type`: `ZHI_RELATION_TYPE:<ZhiRelationType.name>`\n+- `zhi_relation[*].members[*]`: `ZHI:<Zhi.name>`\n+- `wuxing_proportions`: key 为 `WUXING:<Wuxing.name>`\n+- `shishen_proportions`: key 为 `SHISHEN:<Shishen.name>`\n+- `shenqiangshenruo`: `SHENQIANGRUO:<ShenQiangRuo.name>`（`QIANG`/`ZHONGHE`/`RUO`）\n+- `shengxiao`: `SHENGXIAO:<Shengxiao.name>`\n+- `geju`: `GEJU:<GejuEnum.name>` 列表

**枚举定义位置**
- `bazi/core/property.py`

## 基础排盘结果（不含大运）

**入口方法**
- `BaziChartAnalyseFrame.generate_basic_res_without_yun()`

**输出**
- 与基础排盘结果一致，但移除 `yun` 字段

## 分析摘要文本

**入口方法**
- `BaziChartAnalyseFrame.get_analysis_summary()`

**输出**
```json
{
  "ans": "主日志输出内容",
  "liupan": "流年大运排盘文本",
  "guji": "古籍参考文本"
}
```

## 流年查询（定位某一年）

**入口方法**
- `BaziChartAnalyseFrame.find_yun_liu_nian_liuyue(target_year)`

**输出**
- 命中则返回文本字符串（用于展示）
- 未命中返回 `null`

## 神煞查询（指定日期）

**入口方法**
- `BaziChartAnalyseFrame.query_shensha_for_datetime(year, month, day, hour=None)`

**输出**
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
说明：`shensha` 内的列表项为 `SHENSHA:<ShenshaEnum.value>`。

## 神煞影响查询（指定日期）

**入口方法**
- `BaziChartAnalyseFrame.query_shensha_impact_for_datetime(year, month, day, hour=None)`

**输出**
```json
{
  "date": "YYYY-MM-DD HH:00",
  "bazi": {
    "year": {"gan": "GAN:JIA", "zhi": "ZHI:ZI"},
    "month": {"gan": "GAN:YI", "zhi": "ZHI:CHOU"},
    "day": {"gan": "GAN:BING", "zhi": "ZHI:YIN"},
    "hour": {"gan": "GAN:DING", "zhi": "ZHI:MAO"}
  },
  "shensha": {"year": [], "month": [], "day": [], "hour": []},
  "impact": {
    "year": [{"name": "SHENSHA:GUCHEN", "impact": {"career": 0, "love": 0, "study": 0, "health": 0, "life": 0, "spirituality": 0, "interpersonal": 0, "overall": 0}}],
    "month": [],
    "day": [],
    "hour": []
  }
}
```
说明：`shensha` 与 `impact[*].name` 均为 `SHENSHA:<ShenshaEnum.value>`。
