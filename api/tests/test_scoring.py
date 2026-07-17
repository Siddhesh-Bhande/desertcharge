import math

from desertcharge.scoring import (
    HexScoreResult,
    ScoreBand,
    band_for_score,
    clamp,
    desert_score,
    normalize,
    score_hex,
    supply_gap,
)


def test_band_for_score_boundaries() -> None:
    assert band_for_score(0) is ScoreBand.SERVED
    assert band_for_score(20) is ScoreBand.SERVED
    assert band_for_score(21) is ScoreBand.GOOD
    assert band_for_score(40) is ScoreBand.GOOD
    assert band_for_score(41) is ScoreBand.MODERATE
    assert band_for_score(60) is ScoreBand.MODERATE
    assert band_for_score(61) is ScoreBand.POOR
    assert band_for_score(80) is ScoreBand.POOR
    assert band_for_score(81) is ScoreBand.DESERT
    assert band_for_score(100) is ScoreBand.DESERT


def test_band_label_and_color() -> None:
    assert ScoreBand.SERVED.label == "served"
    assert ScoreBand.SERVED.color == "#1B9E8A"
    assert ScoreBand.DESERT.label == "desert"
    assert ScoreBand.DESERT.color == "#B23A24"


def test_clamp() -> None:
    assert clamp(-1.0, 0.0, 1.0) == 0.0
    assert clamp(0.5, 0.0, 1.0) == 0.5
    assert clamp(2.0, 0.0, 1.0) == 1.0


def test_normalize_basic() -> None:
    assert normalize(50.0, 0.0, 100.0) == 0.5
    assert normalize(0.0, 0.0, 100.0) == 0.0
    assert normalize(100.0, 0.0, 100.0) == 1.0


def test_normalize_degenerate_range_returns_zero() -> None:
    assert normalize(5.0, 5.0, 5.0) == 0.0


def test_normalize_clamps_outside_range() -> None:
    assert normalize(-10.0, 0.0, 100.0) == 0.0
    assert normalize(150.0, 0.0, 100.0) == 1.0


def test_supply_gap_far_and_empty_is_worst() -> None:
    # 30+ miles away, zero chargers -> full supply gap
    assert supply_gap(nearest_dc_fast_miles=40.0, weighted_chargers_10mi=0.0) == 1.0


def test_supply_gap_close_and_dense_is_best() -> None:
    # on top of chargers, 3+ weighted ports within 10mi -> no supply gap
    assert supply_gap(nearest_dc_fast_miles=0.0, weighted_chargers_10mi=3.0) == 0.0


def test_desert_score_high_demand_no_supply() -> None:
    # full demand, full supply gap -> 100
    score = desert_score(
        population=1000.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=40.0,
        weighted_chargers_10mi=0.0,
    )
    assert score == 100


def test_desert_score_zero_demand_is_zero() -> None:
    # no people means it is not a charging desert regardless of supply
    score = desert_score(
        population=0.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=40.0,
        weighted_chargers_10mi=0.0,
    )
    assert score == 0


def test_desert_score_matches_formula() -> None:
    # Demand is log-normalized; pop_min=0 so log1p(pop_min)=0.
    demand_norm = math.log1p(250.0) / math.log1p(1000.0)
    gap = supply_gap(nearest_dc_fast_miles=15.0, weighted_chargers_10mi=1.5)
    expected = round(100 * math.sqrt(demand_norm) * gap)
    score = desert_score(
        population=250.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=15.0,
        weighted_chargers_10mi=1.5,
    )
    assert score == expected


def test_desert_score_is_bounded_0_100() -> None:
    score = desert_score(
        population=1_000_000.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=999.0,
        weighted_chargers_10mi=0.0,
    )
    assert 0 <= score <= 100


def test_score_hex_returns_result_with_factors() -> None:
    result = score_hex(
        population=250.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=41.0,
        weighted_chargers_10mi=0.0,
    )
    assert isinstance(result, HexScoreResult)
    assert 0 <= result.score <= 100
    assert result.band.label in {"served", "good", "moderate", "poor", "desert"}
    assert result.nearest_dc_fast_miles == 41.0
    assert result.chargers_10mi == 0.0
    assert result.population == 250.0


def test_score_hex_band_matches_score() -> None:
    result = score_hex(
        population=1000.0,
        pop_min=0.0,
        pop_max=1000.0,
        nearest_dc_fast_miles=40.0,
        weighted_chargers_10mi=0.0,
    )
    assert result.score == 100
    assert result.band.label == "desert"
