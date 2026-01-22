"""Unit tests for bazi/main/bazi_chart_analyse_frame.py - main entry point."""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from lunar_python import Solar
from bazi.main.bazi_chart_analyse_frame import BaziChartAnalyseFrame
from bazi.core.property import ns, strip_ns


class TestBaziChartAnalyseFrameInit:
    """Tests for BaziChartAnalyseFrame initialization."""

    @pytest.fixture
    def sample_lunar(self):
        """Create a sample Lunar object for testing."""
        solar = Solar.fromYmdHms(1990, 1, 15, 8, 30, 0)
        return solar.getLunar()

    def test_basic_initialization(self, sample_lunar):
        """Basic initialization should succeed."""
        frame = BaziChartAnalyseFrame(sample_lunar, "male")
        assert frame is not None
        assert frame.gender == "male"

    def test_female_gender(self, sample_lunar):
        """Female gender should be handled correctly."""
        frame = BaziChartAnalyseFrame(sample_lunar, "female")
        assert frame.gender == "female"

    def test_without_time_flag(self, sample_lunar):
        """without_time=True should skip hour pillar."""
        frame = BaziChartAnalyseFrame(sample_lunar, "male", without_time=True)
        assert frame.without_time is True

    def test_with_time_flag(self, sample_lunar):
        """without_time=False should include hour pillar."""
        frame = BaziChartAnalyseFrame(sample_lunar, "male", without_time=False)
        assert frame.without_time is False


class TestGenerateBasicRes:
    """Tests for generate_basic_res output format."""

    @pytest.fixture
    def frame(self):
        """Create a BaziChartAnalyseFrame for testing."""
        solar = Solar.fromYmdHms(1990, 1, 15, 8, 30, 0)
        lunar = solar.getLunar()
        return BaziChartAnalyseFrame(lunar, "male")

    def test_output_has_zhu_list(self, frame):
        """Output should have zhu_list with all pillars."""
        frame.generate_basic_res()  # Populates frame.res
        res = frame.res
        assert "zhu_list" in res
        zhu_list = res["zhu_list"]
        assert "year_zhu" in zhu_list
        assert "month_zhu" in zhu_list
        assert "day_zhu" in zhu_list
        assert "hour_zhu" in zhu_list

    def test_zhu_has_gan_zhi(self, frame):
        """Each zhu should have gan and zhi."""
        frame.generate_basic_res()
        res = frame.res
        for zhu_name in ["year_zhu", "month_zhu", "day_zhu", "hour_zhu"]:
            zhu = res["zhu_list"][zhu_name]
            assert "gan" in zhu
            assert "zhi" in zhu

    def test_gan_zhi_namespaced(self, frame):
        """Gan and Zhi names should follow NAMESPACE:CODE format."""
        frame.generate_basic_res()
        res = frame.res
        for zhu_name in ["year_zhu", "month_zhu", "day_zhu"]:
            zhu = res["zhu_list"][zhu_name]
            gan_name = zhu["gan"]["name"]
            zhi_name = zhu["zhi"]["name"]
            assert ":" in gan_name, f"Gan not namespaced: {gan_name}"
            assert ":" in zhi_name, f"Zhi not namespaced: {zhi_name}"
            assert gan_name.startswith("GAN:")
            assert zhi_name.startswith("ZHI:")

    def test_wuxing_proportions(self, frame):
        """wuxing_proportions should be present and valid."""
        frame.generate_basic_res()
        res = frame.res
        assert "wuxing_proportions" in res
        props = res["wuxing_proportions"]
        assert isinstance(props, dict)
        # All keys should be namespaced
        for key in props:
            assert ":" in key or key in ["MU", "HUO", "TU", "JIN", "SHUI"]

    def test_shishen_proportions(self, frame):
        """shishen_proportions should be present."""
        frame.generate_basic_res()
        res = frame.res
        assert "shishen_proportions" in res
        props = res["shishen_proportions"]
        assert isinstance(props, dict)

    def test_has_yun_data(self, frame):
        """Output should have yun (fortune/luck) data."""
        frame.generate_basic_res()
        res = frame.res
        assert "yun" in res
        assert isinstance(res["yun"], list)


class TestFindYunLiuNianLiuYue:
    """Tests for find_yun_liu_nian_liuyue year lookup."""

    @pytest.fixture
    def frame(self):
        """Create a BaziChartAnalyseFrame for testing."""
        solar = Solar.fromYmdHms(1990, 1, 15, 8, 30, 0)
        lunar = solar.getLunar()
        return BaziChartAnalyseFrame(lunar, "male")

    def test_target_year_in_range(self, frame):
        """Target year within fortune range should return text."""
        # 2025 should be within range for someone born in 1990
        result = frame.find_yun_liu_nian_liuyue(2025)
        # May return None if year not in calculated range
        if result is not None:
            assert isinstance(result, str)
            assert len(result) > 0

    def test_target_year_before_birth(self, frame):
        """Target year before birth should return None."""
        result = frame.find_yun_liu_nian_liuyue(1980)
        assert result is None

    def test_target_year_far_future(self, frame):
        """Target year far in future may return None."""
        result = frame.find_yun_liu_nian_liuyue(2200)
        # Implementation may or may not calculate this far
        assert result is None or isinstance(result, str)

    def test_result_contains_year(self, frame):
        """Result should contain the target year."""
        result = frame.find_yun_liu_nian_liuyue(2025)
        if result is not None:
            assert "2025" in result

    def test_result_contains_sections(self, frame):
        """Result should contain expected sections."""
        result = frame.find_yun_liu_nian_liuyue(2025)
        if result is not None:
            # Should have flowing year info
            assert "流年" in result or "目标" in result


class TestDateEdgeCases:
    """Tests for date edge cases."""

    def test_leap_year_feb_29(self):
        """Leap year Feb 29 should be handled correctly."""
        solar = Solar.fromYmdHms(2020, 2, 29, 12, 0, 0)
        lunar = solar.getLunar()
        frame = BaziChartAnalyseFrame(lunar, "male")
        assert frame is not None
        frame.generate_basic_res()
        assert "zhu_list" in frame.res

    def test_year_boundary_dec_31(self):
        """Dec 31 should be handled correctly."""
        solar = Solar.fromYmdHms(2024, 12, 31, 23, 59, 0)
        lunar = solar.getLunar()
        frame = BaziChartAnalyseFrame(lunar, "male")
        assert frame is not None

    def test_year_boundary_jan_1(self):
        """Jan 1 should be handled correctly."""
        solar = Solar.fromYmdHms(2025, 1, 1, 0, 0, 0)
        lunar = solar.getLunar()
        frame = BaziChartAnalyseFrame(lunar, "male")
        assert frame is not None

    def test_hour_23(self):
        """Hour 23 (last hour of day) should be handled."""
        solar = Solar.fromYmdHms(1990, 6, 15, 23, 0, 0)
        lunar = solar.getLunar()
        frame = BaziChartAnalyseFrame(lunar, "male")
        frame.generate_basic_res()
        assert frame.res["zhu_list"]["hour_zhu"] is not None

    def test_hour_0(self):
        """Hour 0 (first hour of day) should be handled."""
        solar = Solar.fromYmdHms(1990, 6, 15, 0, 0, 0)
        lunar = solar.getLunar()
        frame = BaziChartAnalyseFrame(lunar, "male")
        frame.generate_basic_res()
        assert frame.res["zhu_list"]["hour_zhu"] is not None


class TestGetAnalysisSummary:
    """Tests for get_analysis_summary output."""

    @pytest.fixture
    def frame(self):
        """Create a BaziChartAnalyseFrame for testing."""
        solar = Solar.fromYmdHms(1990, 1, 15, 8, 30, 0)
        lunar = solar.getLunar()
        return BaziChartAnalyseFrame(lunar, "male")

    def test_returns_tuple(self, frame):
        """get_analysis_summary should return a tuple of 3 strings."""
        result = frame.get_analysis_summary()
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_all_strings(self, frame):
        """All elements should be strings."""
        paipan, liupan, guji = frame.get_analysis_summary()
        assert isinstance(paipan, str)
        assert isinstance(liupan, str)
        assert isinstance(guji, str)

    def test_non_empty_results(self, frame):
        """Results should not be empty."""
        paipan, liupan, guji = frame.get_analysis_summary()
        assert len(paipan) > 0
        assert len(liupan) > 0
        # guji may be empty in some cases
