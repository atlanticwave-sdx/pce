from dataclasses import dataclass
from typing import List, Mapping

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass(frozen=True)
class ConnectionRequest:
    """
    A connection request.

    Connection requests consist of (source, dest, required bandwidth,
    required latency).
    """

    source: int
    destination: int
    required_bandwidth: float
    required_latency: float

    # Make ConnectionRequest hashable since it is used as key in
    # ConnectionSolution
    def __hash__(self):
        return hash(repr(self))


@dataclass_json
@dataclass(frozen=True)
class TrafficMatrix:
    """
    A traffic matrix is a list of connection requests.

    Traffic matrix is input to TE Solver.
    """

    connection_requests: List[ConnectionRequest]
    request_id: str


@dataclass_json
@dataclass(frozen=True)
class ConnectionPath:
    """
    A connection between two nodes.
    """

    source: int
    destination: int


@dataclass_json
@dataclass(frozen=True)
class ConnectionSolution:
    """
    A map from connection requests to connection paths.

    TE Solver's result is represented as a ConnectionSolution.
    """

    connection_map: Mapping[ConnectionRequest, List[ConnectionPath]]
    cost: float
    request_id: str


# The classess below should help us construct a breakdown of the below
# form that pertains to one domain:
#
#     {
#         "name": "TENET_vlan_201_203_Ampath_Tenet",
#         "dynamic_backup_path": true,
#         "uni_a": {
#             "tag": {
#                 "value": 203,
#                 "tag_type": 1
#             },
#             "interface_id": "cc:00:00:00:00:00:00:07:41"
#         },
#         "uni_z": {
#             "tag": {
#                 "value": 201,
#                 "tag_type": 1
#             },
#             "interface_id": "cc:00:00:00:00:00:00:08:50"
#         }
#     }


@dataclass_json
@dataclass(frozen=True)
class VlanTag:
    """
    Representation of a VLAN tag.

    TODO: document tag_type.
    """

    value: int
    tag_type: int


@dataclass_json
@dataclass(frozen=True)
class VlanTaggedPort:
    """
    Representation of a port.
    """

    tag: VlanTag
    port_id: str


@dataclass_json
@dataclass(frozen=True)
class VlanTaggedBreakdown:
    """
    Path breakdown within a single domain with VLAN assignments.
    """

    name: str
    dynamic_backup_path: bool
    uni_a: VlanTaggedPort
    uni_z: VlanTaggedPort


@dataclass_json
@dataclass(frozen=True)
class VlanTaggedBreakdowns:
    """
    Mapping from domain to breakdown.
    """

    breakdowns: Mapping[str, VlanTaggedBreakdown]
