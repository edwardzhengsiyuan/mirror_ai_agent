#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List


class BaziBasicResponse(BaseModel):
    zhu_list: ZhuList = Field(
        description="柱列表"
    )

    nayin: List[str] = Field(
        description="纳音"
    )

    daygan_dishi: List[str] = Field(
        description="日干地势"
    )

    zizuo_dishi: List[str] = Field(
        description="自坐地势"
    )

    shensha: List[ShenSha] = Field(
        description="神煞"
    )

    xunkong: List[str] = Field(
        description="旬空"
    )

    startyun: List[int] = Field(
        description="起运年月日时"
    )

    yun: List[Yun] = Field(
        description="大运"
    )


class ZhuList(BaseModel):
    """
    柱列表
    """
    year_zhu: Zhu = Field(
        description="年柱"
    )
    month_zhu: Zhu = Field(
        description="月柱"
    )
    day_zhu: Zhu = Field(
        description="日柱"
    )
    hour_zhu: Zhu = Field(
        description="时柱"
    )
    taiyuan_zhu: Zhu = Field(
        description="胎元柱"
    )
    minggong_zhu: Zhu = Field(
        description="命宫柱"
    )
    shengong_zhu: Zhu = Field(
        description="身宫柱"
    )


class Zhu(BaseModel):
    """
    柱: 干支
    """
    gan: Gan = Field(
        description="干"
    )
    zhi: Zhi = Field(
        description="支"
    )


class Gan(BaseModel):
    name: str = Field(
        description="干"
    )
    wuxing: str = Field(
        description="五行"
    )
    yinyang: str = Field(
        description="阴阳"
    )
    shishen: str = Field(
        description="十神"
    )


class Zhi(BaseModel):
    """
    支: 干支
    """
    name: str = Field(
        description="支"
    )
    wuxing: str = Field(
        description="五行"
    )
    yinyang: str = Field(
        description="阴阳"
    )
    hidden_gans: List[Gan] = Field(
        description="藏干"
    )


class ShenSha(BaseModel):
    """
    神煞
    """
    values: List[str] = Field(
        description="神煞"
    )


class Yun(BaseModel):
    """
    运
    """
    year: int = Field(
        description="年份"
    )
    age: int = Field(
        description="年龄"
    )
    gan: str = Field(
        description="干",
        default=None
    )
    zhi: str = Field(
        description="支",
        default=None
    )
    gan_wuxing: str = Field(
        description="干五行",
        default=None
    )
    zhi_wuxing: str = Field(
        description="支五行",
        default=None
    )
    gan_shishen: str = Field(
        description="干十神",
        default=None
    )
    zhi_shishen: str = Field(
        description="支十神",
        default=None
    )
    liunian: List[LiuNian] = Field(
        description="流年",
        default=None
    )
    shensha: List[str] = Field(
        description="神煞",
        default=None
    )
    gan_relation: List[str] = Field(
        description="干关系",
        default=None
    )
    zhi_relation: List[str] = Field(
        description="支关系",
        default=None
    )


class LiuNian(BaseModel):
    """
    流年
    """
    year: int = Field(
        description="年份"
    )
    age: int = Field(
        description="年龄"
    )
    gan: str = Field(
        description="干"
    )
    zhi: str = Field(
        description="支"
    )
    gan_wuxing: str = Field(
        description="干五行"
    )
    zhi_wuxing: str = Field(
        description="支五行"
    )
    gan_shishen: str = Field(
        description="干十神"
    )
    zhi_shishen: str = Field(
        description="支十神"
    )
    liuyue: List[LiuYue] = Field(
        description="流月"
    )
    shensha: List[str] = Field(
        description="神煞"
    )
    gan_relation: List[str] = Field(
        description="干关系"
    )
    zhi_relation: List[str] = Field(
        description="支关系"
    )


class LiuYue(BaseModel):
    """
    流月
    """
    month: int = Field(
        description="月份"
    )
    day: int = Field(
        description="日"
    )
    gan: str = Field(
        description="干"
    )
    zhi: str = Field(
        description="支"
    )
    gan_wuxing: str = Field(
        description="干五行"
    )
    zhi_wuxing: str = Field(
        description="支五行"
    )
    gan_shishen: str = Field(
        description="干十神"
    )
    zhi_shishen: str = Field(
        description="支十神"
    )
    gan_relation: List[str] = Field(
        description="干关系"
    )
    zhi_relation: List[str] = Field(
        description="支关系"
    )


if __name__ == "__main__":
    print(BaziBasicResponse.model_json_schema())
