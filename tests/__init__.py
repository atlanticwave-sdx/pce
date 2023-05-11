import pathlib


class TestData:
    TEST_DATA_DIR = pathlib.Path(__file__).parent / "data"

    TOPOLOGY_DATA_DIR = TEST_DATA_DIR / "topologies"

    TOPOLOGY_FILE_SDX = TEST_DATA_DIR / "sdx.json"
    
    TOPOLOGY_FILE_ZAOXI = TOPOLOGY_DATA_DIR / "zaoxi.json"
    TOPOLOGY_FILE_SAX = TOPOLOGY_DATA_DIR / "sax.json"
    TOPOLOGY_FILE_AMLIGHT = TOPOLOGY_DATA_DIR / "amlight.json"

    TOPOLOGY_FILE_AMLIGHT_IMG = TOPOLOGY_DATA_DIR / "amlight.png"

    CONNECTION_REQ_FILE = TEST_DATA_DIR / "test_request.json"

    TOPOLOGY_FILE_SAX_2 = TEST_DATA_DIR / "sax-2.json"
    CONNECTION_REQ_FILE_SAX_2_INVALID = TEST_DATA_DIR / "sax-2-request-invalid.json"
    CONNECTION_REQ_FILE_SAX_2_VALID = TEST_DATA_DIR / "sax-2-request-valid.json"
