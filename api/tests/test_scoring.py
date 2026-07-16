from desertcharge.scoring import ScoreBand, band_for_score


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
