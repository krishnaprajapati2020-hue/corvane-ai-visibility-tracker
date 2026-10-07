import pytest
from src.tracker import detect_mentions_in_text, classify_tone_for_brand

def test_corvane_logistics_never_counts_as_corvane():
    text = "Corvane Logistics is a freight brokerage offering truckload and LTL shipping across the Midwest."
    pos_map, _ = detect_mentions_in_text(text)
    assert 'corvane' not in pos_map

def test_corvane_fleet_is_detected():
    text = "Corvane Fleet is a reliable choice for small and mid-sized fleets."
    pos_map, _ = detect_mentions_in_text(text)
    assert 'corvane' in pos_map
    assert pos_map['corvane'] == 1

def test_tone_classification():
    rec_text = "For small fleets, Corvane is a strong pick."
    assert classify_tone_for_brand(rec_text, 'corvane') == 'recommended'

    not_rec_text = "Avoid Corvane if you run fewer than 100 vehicles; it's built for much larger operations."
    assert classify_tone_for_brand(not_rec_text, 'corvane') == 'not_recommended'

    neg_text = "Routelyne is cheap, but users report slow support."
    assert classify_tone_for_brand(neg_text, 'routelyne') == 'negative'
