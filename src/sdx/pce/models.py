from dataclasses import dataclass
from typing import List, Mapping

from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
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


@dataclass_json
@dataclass
class TrafficMatrix:
    """
    A traffic matrix is a list of connection requests.

    Traffic matrix is input to TE Solver.
    """

    connection_requests: List[ConnectionRequest]


@dataclass_json
@dataclass
class ConnectionPath:
    """
    A connection between two nodes.
    """

    source: int
    destination: int


@dataclass_json
@dataclass
class ConnectionSolution:
    """
    A map from connection requests to connection paths.

    TE Solver's result is represented as a ConnectionSolution.
    """

    solution: Mapping[ConnectionRequest, List[ConnectionPath]]
