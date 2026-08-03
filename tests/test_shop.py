from chatgr_core.core.shop import buy_item, ensure_inventory, format_shop


def test_buy_emoji_pack():
    profile = ensure_inventory({"coins": 100, "achievements": []})
    profile, msg = buy_item(profile, "emoji_rich")
    assert profile["coins"] == 85
    assert "emoji_rich" in profile["inventory"]["flags"]
    assert "Куплено" in msg


def test_buy_not_enough():
    profile = ensure_inventory({"coins": 1, "achievements": []})
    profile, msg = buy_item(profile, "title_tiger")
    assert profile["coins"] == 1
    assert "Не хватает" in msg


def test_format_shop():
    text = format_shop({"coins": 10})
    assert "Магазин" in text
