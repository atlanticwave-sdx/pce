from dataclasses import dataclass
from typing import List, Mapping, Union

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
    required_bandwidth: Union[float, None] = None
    required_latency: Union[float, None] = None

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
