import pathlib
from importlib.resources import files


class TestData:
    # Some data files are in src/sdx/pce/data.
    PACKAGE_DATA_DIR = files("sdx.pce.data")

    TOPOLOGY_FILE_ZAOXI = PACKAGE_DATA_DIR / "topologies" / "zaoxi.json"
    TOPOLOGY_FILE_SAX = PACKAGE_DATA_DIR / "topologies" / "sax.json"
    TOPOLOGY_FILE_AMLIGHT = PACKAGE_DATA_DIR / "topologies" / "amlight.json"
    CONNECTION_REQ = PACKAGE_DATA_DIR / "requests" / "test_request.json"

    TEST_DATA_DIR = pathlib.Path(__file__).parent / "data"

    TOPOLOGY_DATA_DIR = TEST_DATA_DIR / "topologies"

    TOPOLOGY_FILE_SDX = TEST_DATA_DIR / "sdx.json"

    TOPOLOGY_FILE_AMLIGHT_IMG = TOPOLOGY_DATA_DIR / "amlight.png"

    CONNECTION_REQ_AMLIGHT = TEST_DATA_DIR / "test_request_amlight.json"

    TOPOLOGY_FILE_SAX_2 = TEST_DATA_DIR / "sax-2.json"
    CONNECTION_REQ_FILE_SAX_2_INVALID = TEST_DATA_DIR / "sax-2-request-invalid.json"
    CONNECTION_REQ_FILE_SAX_2_VALID = TEST_DATA_DIR / "sax-2-request-valid.json"
