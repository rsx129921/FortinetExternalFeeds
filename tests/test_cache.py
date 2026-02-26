from app.cache import FeedCache


def test_empty_cache():
    cache = FeedCache()
    assert cache.get_tag("AzureCloud") is None
    assert cache.get_all_tags() == []
    assert cache.change_number is None
    assert cache.last_refresh is None


def test_load_data():
    cache = FeedCache()
    sample_data = {
        "changeNumber": 100,
        "cloud": "Public",
        "values": [
            {
                "name": "AzureCloud",
                "id": "AzureCloud",
                "properties": {
                    "changeNumber": 50,
                    "region": "",
                    "regionId": 0,
                    "platform": "Azure",
                    "systemService": "",
                    "addressPrefixes": [
                        "10.0.0.0/8",
                        "172.16.0.0/12",
                        "2001:db8::/32",
                    ],
                    "networkFeatures": ["API", "NSG"],
                },
            },
        ],
    }
    cache.load(sample_data)
    assert cache.change_number == 100
    assert cache.last_refresh is not None
    assert cache.get_all_tags() == ["AzureCloud"]


def test_get_tag_ipv4_only():
    cache = FeedCache()
    cache.load({
        "changeNumber": 1,
        "cloud": "Public",
        "values": [
            {
                "name": "TestTag",
                "id": "TestTag",
                "properties": {
                    "changeNumber": 1,
                    "region": "",
                    "regionId": 0,
                    "platform": "Azure",
                    "systemService": "",
                    "addressPrefixes": [
                        "10.0.0.0/8",
                        "192.168.1.0/24",
                        "2001:db8::/32",
                    ],
                    "networkFeatures": [],
                },
            },
        ],
    })
    result = cache.get_tag("TestTag", include_ipv6=False)
    assert result == ["10.0.0.0/8", "192.168.1.0/24"]


def test_get_tag_with_ipv6():
    cache = FeedCache()
    cache.load({
        "changeNumber": 1,
        "cloud": "Public",
        "values": [
            {
                "name": "TestTag",
                "id": "TestTag",
                "properties": {
                    "changeNumber": 1,
                    "region": "",
                    "regionId": 0,
                    "platform": "Azure",
                    "systemService": "",
                    "addressPrefixes": [
                        "10.0.0.0/8",
                        "2001:db8::/32",
                    ],
                    "networkFeatures": [],
                },
            },
        ],
    })
    result = cache.get_tag("TestTag", include_ipv6=True)
    assert result == ["10.0.0.0/8", "2001:db8::/32"]


def test_get_nonexistent_tag():
    cache = FeedCache()
    cache.load({
        "changeNumber": 1,
        "cloud": "Public",
        "values": [],
    })
    assert cache.get_tag("DoesNotExist") is None
