import pathlib
import tempfile
from importlib.resources import files


class TestData:
    # Some data files are in src/sdx/pce/data.
    PACKAGE_DATA_DIR = files("sdx.pce") / "data"

    TOPOLOGY_FILE_ZAOXI = PACKAGE_DATA_DIR / "topologies" / "zaoxi.json"
    TOPOLOGY_FILE_SAX = PACKAGE_DATA_DIR / "topologies" / "sax.json"
    TOPOLOGY_FILE_AMLIGHT = PACKAGE_DATA_DIR / "topologies" / "amlight.json"
    CONNECTION_REQ = PACKAGE_DATA_DIR / "requests" / "test_request.json"

    # Write test output files in OS temporary directory.
    TEST_OUTPUT_DIR = pathlib.Path(tempfile.gettempdir())
    TEST_OUTPUT_IMG_AMLIGHT = TEST_OUTPUT_DIR / "sdx-pce-amlight.png"
    TEST_OUTPUT_IMG_SAX = TEST_OUTPUT_DIR / "sdx-pce-sax.png"
    TEST_OUTPUT_IMG_ZAOXI = TEST_OUTPUT_DIR / "sdx-pce-zaoxi.png"

    # Other test data files.
    TEST_DATA_DIR = pathlib.Path(__file__).parent / "data"

    TOPOLOGY_FILE_SDX = TEST_DATA_DIR / "sdx.json"
    CONNECTION_REQ_AMLIGHT = TEST_DATA_DIR / "test_request_amlight.json"

    TOPOLOGY_FILE_SAX_2 = TEST_DATA_DIR / "sax-2.json"
    CONNECTION_REQ_FILE_SAX_2_INVALID = TEST_DATA_DIR / "sax-2-request-invalid.json"
    CONNECTION_REQ_FILE_SAX_2_VALID = TEST_DATA_DIR / "sax-2-request-valid.json"
