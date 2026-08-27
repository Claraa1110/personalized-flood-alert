from app.api.geocode import _build_tw_address


def test_composes_city_district_and_road():
    addr = {"city": "臺北市", "city_district": "信義區", "road": "信義路五段"}
    assert _build_tw_address(addr) == "臺北市信義區信義路五段"


def test_falls_back_from_city_to_county_to_state():
    assert _build_tw_address({"county": "宜蘭縣", "town": "礁溪鄉"}) == "宜蘭縣礁溪鄉"
    assert _build_tw_address({"state": "臺灣省", "suburb": "東區"}) == "臺灣省東區"


def test_prefers_city_over_county():
    addr = {"city": "臺中市", "county": "臺中縣", "road": "臺灣大道"}
    assert _build_tw_address(addr) == "臺中市臺灣大道"


def test_falls_back_through_the_district_alternatives():
    base = {"city": "新北市", "road": "中山路"}
    assert _build_tw_address({**base, "suburb": "板橋區"}) == "新北市板橋區中山路"
    assert _build_tw_address({**base, "town": "板橋"}) == "新北市板橋中山路"
    assert _build_tw_address({**base, "village": "民生里"}) == "新北市民生里中山路"


def test_falls_back_through_the_road_alternatives():
    base = {"city": "高雄市", "suburb": "鹽埕區"}
    assert _build_tw_address({**base, "pedestrian": "行人徒步區"}).endswith("行人徒步區")
    assert _build_tw_address({**base, "footway": "小徑"}).endswith("小徑")


def test_uses_display_name_when_nothing_composable_is_present():
    addr = {"display_name": "臺灣, 某處"}
    assert _build_tw_address(addr) == "臺灣, 某處"


def test_returns_empty_string_for_an_empty_address():
    assert _build_tw_address({}) == ""


def test_partial_components_still_produce_a_usable_string():
    assert _build_tw_address({"city": "臺南市"}) == "臺南市"
    assert _build_tw_address({"road": "中正路"}) == "中正路"
