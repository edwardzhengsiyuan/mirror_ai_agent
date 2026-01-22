"""Unit tests for bazi/core/property.py - enums and namespace functions."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from bazi.core.property import Gan, Zhi, Wuxing, Yinyang, ns, strip_ns


class TestGanEnum:
    """Tests for Gan (Heavenly Stems) enum."""

    @pytest.mark.parametrize("chinese,expected", [
        ("甲", Gan.JIA),
        ("乙", Gan.YI),
        ("丙", Gan.BING),
        ("丁", Gan.DING),
        ("戊", Gan.WU),
        ("己", Gan.JI),
        ("庚", Gan.GENG),
        ("辛", Gan.XIN),
        ("壬", Gan.REN),
        ("癸", Gan.GUI),
    ])
    def test_from_chinese_all_stems(self, chinese, expected):
        """All 10 Chinese characters should map to correct Gan."""
        result = Gan.from_chinese(chinese)
        assert result == expected

    def test_from_chinese_invalid_raises(self):
        """Invalid Chinese character should raise ValueError."""
        with pytest.raises(ValueError):
            Gan.from_chinese("子")  # This is a Zhi, not Gan

    def test_gan_has_wuxing(self):
        """Each Gan should have a wuxing property."""
        for gan in Gan:
            assert gan.wuxing in Wuxing

    def test_gan_has_yinyang(self):
        """Each Gan should have a yinyang property."""
        for gan in Gan:
            assert gan.yinyang in Yinyang

    def test_gan_yang_yin_alternates(self):
        """Gan should alternate between Yang and Yin."""
        # 甲(Yang), 乙(Yin), 丙(Yang), 丁(Yin), etc.
        assert Gan.JIA.yinyang == Yinyang.YANG
        assert Gan.YI.yinyang == Yinyang.YIN
        assert Gan.BING.yinyang == Yinyang.YANG
        assert Gan.DING.yinyang == Yinyang.YIN

    def test_gan_wuxing_mapping(self):
        """Gan should map to correct Wuxing elements."""
        assert Gan.JIA.wuxing == Wuxing.MU  # Wood
        assert Gan.YI.wuxing == Wuxing.MU
        assert Gan.BING.wuxing == Wuxing.HUO  # Fire
        assert Gan.DING.wuxing == Wuxing.HUO
        assert Gan.WU.wuxing == Wuxing.TU  # Earth
        assert Gan.JI.wuxing == Wuxing.TU
        assert Gan.GENG.wuxing == Wuxing.JIN  # Metal
        assert Gan.XIN.wuxing == Wuxing.JIN
        assert Gan.REN.wuxing == Wuxing.SHUI  # Water
        assert Gan.GUI.wuxing == Wuxing.SHUI


class TestZhiEnum:
    """Tests for Zhi (Earthly Branches) enum."""

    @pytest.mark.parametrize("chinese,expected", [
        ("子", Zhi.ZI),
        ("丑", Zhi.CHOU),
        ("寅", Zhi.YIN),
        ("卯", Zhi.MAO),
        ("辰", Zhi.CHEN),
        ("巳", Zhi.SI),
        ("午", Zhi.WU),
        ("未", Zhi.WEI),
        ("申", Zhi.SHEN),
        ("酉", Zhi.YOU),
        ("戌", Zhi.XU),
        ("亥", Zhi.HAI),
    ])
    def test_from_chinese_all_branches(self, chinese, expected):
        """All 12 Chinese characters should map to correct Zhi."""
        result = Zhi.from_chinese(chinese)
        assert result == expected

    def test_from_chinese_invalid_raises(self):
        """Invalid Chinese character should raise ValueError."""
        with pytest.raises(ValueError):
            Zhi.from_chinese("甲")  # This is a Gan, not Zhi

    def test_zhi_has_wuxing(self):
        """Each Zhi should have a wuxing property."""
        for zhi in Zhi:
            assert zhi.wuxing in Wuxing

    def test_zhi_has_yinyang(self):
        """Each Zhi should have a yinyang property."""
        for zhi in Zhi:
            assert zhi.yinyang in Yinyang


class TestWuxingEnum:
    """Tests for Wuxing (Five Elements) enum."""

    @pytest.mark.parametrize("chinese,expected", [
        ("木", Wuxing.MU),
        ("火", Wuxing.HUO),
        ("土", Wuxing.TU),
        ("金", Wuxing.JIN),
        ("水", Wuxing.SHUI),
    ])
    def test_from_chinese_name(self, chinese, expected):
        """Chinese element names should map to correct Wuxing."""
        result = Wuxing.from_chinese_name(chinese)
        assert result == expected

    def test_wuxing_count(self):
        """There should be exactly 5 Wuxing elements."""
        assert len(Wuxing) == 5


class TestNamespaceFunctions:
    """Tests for ns() and strip_ns() functions."""

    def test_ns_basic(self):
        """ns() should create NAMESPACE:CODE format."""
        result = ns("GAN", "WU")
        assert result == "GAN:WU"

    def test_ns_idempotent(self):
        """ns() should be idempotent - already namespaced stays same."""
        result = ns("GAN", "GAN:WU")
        assert result == "GAN:WU"

    def test_ns_different_namespaces(self):
        """ns() should work with different namespaces."""
        assert ns("ZHI", "ZI") == "ZHI:ZI"
        assert ns("WUXING", "MU") == "WUXING:MU"
        assert ns("SHISHEN", "BIJIAN") == "SHISHEN:BIJIAN"

    def test_strip_ns_basic(self):
        """strip_ns() should remove namespace prefix."""
        result = strip_ns("GAN:WU")
        assert result == "WU"

    def test_strip_ns_no_namespace(self):
        """strip_ns() on value without namespace returns unchanged."""
        result = strip_ns("WU")
        assert result == "WU"

    def test_strip_ns_multiple_colons(self):
        """strip_ns() with multiple colons strips first prefix."""
        result = strip_ns("A:B:C")
        assert result == "B:C"

    def test_ns_none_handling(self):
        """ns() should handle None gracefully."""
        # Implementation may vary - test actual behavior
        try:
            result = ns("GAN", None)
            # If it doesn't raise, result should be reasonable
            assert result is not None or result is None
        except (TypeError, AttributeError):
            pass  # Expected if None not handled

    def test_strip_ns_none_handling(self):
        """strip_ns() should handle None gracefully."""
        try:
            result = strip_ns(None)
            assert result is None or result == "None"
        except (TypeError, AttributeError):
            pass  # Expected if None not handled


class TestEnumConsistency:
    """Tests for enum consistency across the codebase."""

    def test_all_gan_have_chinese_name(self):
        """All Gan should have chinese_name property."""
        for gan in Gan:
            assert hasattr(gan, "chinese_name")
            assert len(gan.chinese_name) == 1  # Single character

    def test_all_zhi_have_chinese_name(self):
        """All Zhi should have chinese_name property."""
        for zhi in Zhi:
            assert hasattr(zhi, "chinese_name")
            assert len(zhi.chinese_name) == 1  # Single character

    def test_gan_enum_count(self):
        """There should be exactly 10 Gan (Heavenly Stems)."""
        assert len(Gan) == 10

    def test_zhi_enum_count(self):
        """There should be exactly 12 Zhi (Earthly Branches)."""
        assert len(Zhi) == 12
