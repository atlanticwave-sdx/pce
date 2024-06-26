import pathlib
import tempfile

try:
    # Use stdlib modules with Python > 3.8.
    from importlib.resources import files
except ImportError:
    # Use compatibility library with Python 3.8.
    from importlib_resources import files


class TestData:
    # Some data files are in src/sdx_datamodel/data.
    TOPOLOGY_DIR = files("sdx_datamodel") / "data" / "topologies"
    TOPOLOGY_FILE_ZAOXI = TOPOLOGY_DIR / "zaoxi.json"
    TOPOLOGY_FILE_SAX = TOPOLOGY_DIR / "sax.json"
    TOPOLOGY_FILE_AMLIGHT = TOPOLOGY_DIR / "amlight.json"
    TOPOLOGY_FILE_SDX = TOPOLOGY_DIR / "sdx.json"
    TOPOLOGY_FILE_AMLIGHT_USER_PORT = TOPOLOGY_DIR / "amlight_user_port.json"

    REQUESTS_DIR = files("sdx_datamodel") / "data" / "requests"
    CONNECTION_REQ = REQUESTS_DIR / "test_request.json"

    # Write test output files in OS temporary directory.
    TEST_OUTPUT_DIR = pathlib.Path(tempfile.gettempdir())
    TEST_OUTPUT_IMG_AMLIGHT = TEST_OUTPUT_DIR / "sdx_pce-amlight.png"
    TEST_OUTPUT_IMG_SAX = TEST_OUTPUT_DIR / "sdx_pce-sax.png"
    TEST_OUTPUT_IMG_ZAOXI = TEST_OUTPUT_DIR / "sdx_pce-zaoxi.png"

    # Other test data files.
    TEST_DATA_DIR = pathlib.Path(__file__).parent / "data"

    CONNECTION_REQ_AMLIGHT = TEST_DATA_DIR / "test_request_amlight.json"
    CONNECTION_REQ_AMLIGHT_USER_PORT = (
        TEST_DATA_DIR / "test_request_amlight_user_port.json"
    )
    CONNECTION_REQ_AMLIGHT_ZAOXI_USER_PORT = (
        TEST_DATA_DIR / "test_request_amlight_zaoxi_user_port.json"
    )

    TOPOLOGY_FILE_SAX_2 = TEST_DATA_DIR / "sax-2.json"
    CONNECTION_REQ_FILE_SAX_2_INVALID = TEST_DATA_DIR / "sax-2-request-invalid.json"
    CONNECTION_REQ_FILE_SAX_2_VALID = TEST_DATA_DIR / "sax-2-request-valid.json"

    CONNECTION_REQ_AMLIGHT_ZAOXI_USER_PORT_v2 = (
        TEST_DATA_DIR / "test_request-amlight_zaoxi-p2p-v2.json"
    )
