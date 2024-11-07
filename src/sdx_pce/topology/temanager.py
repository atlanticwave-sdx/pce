import logging
import threading
from itertools import chain
from typing import List, Optional

import networkx as nx
from networkx.algorithms import approximation as approx
from sdx_datamodel.models.port import Port
from sdx_datamodel.parsing.connectionhandler import ConnectionHandler

from sdx_pce.models import (
    ConnectionPath,
    ConnectionRequest,
    ConnectionSolution,
    TrafficMatrix,
    VlanTag,
    VlanTaggedBreakdown,
    VlanTaggedBreakdowns,
    VlanTaggedPort,
)
from sdx_pce.topology.manager import TopologyManager
from sdx_pce.utils.constants import Constants
from sdx_pce.utils.exceptions import TEError, UnknownRequestError, ValidationError

UNUSED_VLAN = None


class TEManager:
    """
    TE Manager for connection - topology operations.

    Functions of this class are:

        - generate inputs to the PCE solver

        - converter the solver output.

        - VLAN reservation and unreservation.
    """

    def __init__(self, topology_data):
        self.topology_manager = TopologyManager()

        # A lock to safely perform topology operations.
        self._topology_lock = threading.Lock()

        self._logger = logging.getLogger(__name__)

        # Keep a list of solved solution ConnectionSolution:connectionSolution.
        self._connectionSolution_list = []

        # A {domain, {port, {vlan, in_use}}} mapping.
        self._vlan_tags_table = {}

        # Making topology_data optional while investigating
        # https://github.com/atlanticwave-sdx/sdx-controller/issues/145.
        #
        # TODO: a nicer thing to do would be to keep less state around.
        # https://github.com/atlanticwave-sdx/pce/issues/122
        if topology_data:
            self.topology_manager.add_topology(topology_data)
            self.graph = self.generate_graph_te()
            self._update_vlan_tags_table(
                domain_name=topology_data.get("id"),
                port_map=self.topology_manager.get_port_map(),
            )
        else:
            self.graph = None

    def add_topology(self, topology_data: dict):
        """
        Add a new topology to TEManager.

        :param topology_data: a dictionary that represents a topology.
        """
        self.topology_manager.add_topology(topology_data)

        # Ports appear in two places in the combined topology
        # maintained by TopologyManager: attached to each of the
        # nodes, and attached to links.  Here we are using the ports
        # attached to links.
        self._update_vlan_tags_table(
            domain_name=topology_data.get("id"),
            port_map=self.topology_manager.get_port_map(),
        )

    def update_topology(self, topology_data: dict):
        """
        Update an existing topology in TEManager.

        :param topology_data: a dictionary that represents a topology.
        """
        self.topology_manager.update_topology(topology_data)

        # Update vlan_tags_table in a non-disruptive way. Previous concerned
        # still applies:
        # TODO: careful here when updating VLAN tags table -- what do
        # we do when an in use VLAN tag becomes invalid in the update?
        # See https://github.com/atlanticwave-sdx/pce/issues/123
        self._update_vlan_tags_table(
            domain_name=topology_data.get("id"),
            port_map=self.topology_manager.get_port_map(),
        )

    def get_topology_map(self) -> dict:
        """
        Get {topology_id: topology, ..} map.
        """
        return self.topology_manager.get_topology_map()

    def get_port_obj_services_label_range(self, port: Port) -> List[str]:
        vlan_range = None
        services = port.services
        if services and services.l2vpn_ptp:
            vlan_range = services.l2vpn_ptp.get("vlan_range")
        return vlan_range

    def get_failed_links(self) -> List[dict]:
        """Get failed links on the topology (ie., Links not up and enabled)."""
        return self.topology_manager.get_failed_links()

    def get_connections(self) -> List[ConnectionRequest]:
        """Get all the connections in the _connectionSolution_list."""
        connections = []
        for solution in self._connectionSolution_list:
            connections.append(solution.request_id)
        return connections

    def _update_vlan_tags_table(self, domain_name: str, port_map: dict):
        """
        Update VLAN tags table in a non-disruptive way, meaning: only add new
        VLANs to the table. Removed VLANs will need further discussion (see
        https://github.com/atlanticwave-sdx/pce/issues/123)
        """
        self._vlan_tags_table.setdefault(domain_name, {})

        for port_id, port in port_map.items():
            # Get the label range for this port: either from the
            # port itself (v1), or from the services attached to it (v2).
            label_range = self.get_port_obj_services_label_range(port)
            if label_range is None:
                label_range = port.vlan_range

            # TODO: why is label_range sometimes None, and what to
            # do when that happens?
            if label_range is None:
                self._logger.info(f"label_range on {port.id} is None")
                continue

            # label_range is of the form ['100-200', '1000']; let
            # us expand it.  Would have been ideal if this was
            # already in some parsed form, but it is not, so this
            # is a work-around.
            all_labels = self._expand_label_range(label_range)

            self._vlan_tags_table[domain_name].setdefault(port_id, {})
            for label in all_labels:
                self._vlan_tags_table[domain_name][port_id].setdefault(
                    label, UNUSED_VLAN
                )

    def _expand_label_range(self, label_range: []) -> List[int]:
        """
        Expand the label range to a list of numbers.
        """
        labels = [self._expand_label(label) for label in label_range]
        # flatten result and return it.
        return list(chain.from_iterable(labels))

    def _expand_label(self, label) -> List[int]:
        start = stop = 0
        """
        Expand items in label range to a list of numbers.

        Items in label ranges can be of the form "100-200" or "100".
        For the first case, we return [100,101,...200]; for the second
        case, we return [100].
        """
        if isinstance(label, str):
            parts = label.split("-")
            start = int(parts[0])
            stop = int(parts[-1]) + 1

        if isinstance(label, int):
            start = label
            stop = label + 1
        """
        Items in label ranges can be of the form [100, 200].
        For the first case, we return [100,101,...200].
        """
        if isinstance(label, list):
            start = label[0]
            stop = label[1] + 1

        """
        Items in label ranges can not be of the tuple form (100, 200), per JSON schema.
        """

        if start == 0 or stop == 0 or start > stop:
            raise ValidationError(f"Invalid label range: {label}")

        return list(range(start, stop))

    def generate_traffic_matrix(self, connection_request: dict) -> TrafficMatrix:
        """
        Generate a Traffic Matrix from the connection request we have.

        A connection request specifies an ingress port, an egress
        port, and some other properties.  The ports may belong to
        different domains.  We need to break that request down into a
        set of requests, each of them specific to a domain.  We call
        such a domain-wise set of requests a traffic matrix.
        """
        self._logger.info(
            f"generate_traffic_matrix: connection_request: {connection_request}"
        )

        request = ConnectionHandler().import_connection_data(connection_request)

        self._logger.info(f"generate_traffic_matrix: decoded request: {request}")

        ingress_port = request.ingress_port
        egress_port = request.egress_port

        self._logger.info(
            f"generate_traffic_matrix, ports: "
            f"ingress_port.id: {ingress_port.id}, "
            f"egress_port.id: {egress_port.id}"
        )

        topology = self.topology_manager.get_topology()

        ingress_node = topology.get_node_by_port(ingress_port.id)
        egress_node = topology.get_node_by_port(egress_port.id)

        if ingress_node is None:
            self._logger.warning(
                f"No ingress node was found for ingress port ID '{ingress_port.id}'"
            )
            return None

        if egress_node is None:
            self._logger.warning(
                f"No egress node is found for egress port ID '{egress_port.id}'"
            )
            return None

        ingress_nodes = [
            x for x, y in self.graph.nodes(data=True) if y["id"] == ingress_node.id
        ]

        egress_nodes = [
            x for x, y in self.graph.nodes(data=True) if y["id"] == egress_node.id
        ]

        if len(ingress_nodes) <= 0:
            self._logger.warning(
                f"No ingress node '{ingress_node.id}' found in the graph"
            )
            return None

        if len(egress_nodes) <= 0:
            self._logger.warning(
                f"No egress node '{egress_node.id}' found in the graph"
            )
            return None

        required_bandwidth = request.bandwidth_required or 0
        required_latency = request.latency_required or float("inf")
        request_id = request.id

        self._logger.info(
            f"Setting required_latency: {required_latency}, "
            f"required_bandwidth: {required_bandwidth}"
        )

        request = ConnectionRequest(
            source=ingress_nodes[0],
            destination=egress_nodes[0],
            required_bandwidth=required_bandwidth,
            required_latency=required_latency,
        )

        return TrafficMatrix(connection_requests=[request], request_id=request_id)

    def generate_graph_te(self) -> Optional[nx.Graph]:
        """
        Return the topology graph that we have.
        """
        graph = self.topology_manager.generate_graph()

        if graph is None:
            self._logger.warning("No graph could be generated")
            return None

        graph = nx.convert_node_labels_to_integers(graph, label_attribute="id")

        # TODO: why is this needed?
        self.graph = graph
        # print(list(graph.nodes(data=True)))

        return graph

    def graph_node_connectivity(self, source=None, dest=None):
        """
        Check that a source and destination node have connectivity.
        No need to continue if there is no connectiviy between source and destination
        """

        return approx.node_connectivity(self.graph, source, dest)

    def requests_connectivity(self, tm: TrafficMatrix) -> bool:
        """
        Check that connectivity is possible.
        """
        # TODO: consider using filter() and reduce(), maybe?
        # TODO: write some tests for this method.
        for request in tm.connection_requests:
            conn = self.graph_node_connectivity(request.source, request.destination)
            self._logger.info(
                f"Request connectivity: source {request.source}, "
                f"destination: {request.destination} = {conn}"
            )
            if conn is False:
                return False

        return True

    def get_links_on_path(self, solution: ConnectionSolution) -> list:
        """
        Return all the links on a connection solution.

        The result will be a list of dicts, like so:

        .. code-block::

           [{'source': 'urn:ogf:network:sdx:port:zaoxi:A1:1',
              'destination': 'urn:ogf:network:sdx:port:zaoxi:B1:3'},
            {'source': 'urn:ogf:network:sdx:port:zaoxi:B1:1',
             'destination': 'urn:ogf:network:sdx:port:sax:B3:1'},
            {'source': 'urn:ogf:network:sdx:port:sax:B3:3',
             'destination': 'urn:ogf:network:sdx:port:sax:B1:4'},
            {'source': 'urn:ogf:network:sdx:port:sax:B1:1',
             'destination': 'urn:sdx:port:amlight:B1:1'},
            {'source': 'urn:sdx:port:amlight.net:B1:3',
             'destination': 'urn:sdx:port:amlight.net:A1:1'}]

        """
        if solution is None or solution.connection_map is None:
            self._logger.warning(f"Can't find paths for {solution}")
            return None

        result = []

        for connectionRequest, links in solution.connection_map.items():
            for link in links:
                assert isinstance(link, ConnectionPath)

                ports = self._get_ports_by_link(link)

                self._logger.info(f"get_links_on_path: ports: {ports}")

                if ports:
                    p1, p2 = ports
                    result.append({"source": p1["id"], "destination": p2["id"]})

        return connectionRequest, result

    def update_link_bandwidth(self, solution: ConnectionSolution, reduce=True):
        """
        Update the topology properties, typically the link bandwidth property after a place_connection call succeeds
        """
        connectionRequest, links = self.get_links_on_path(solution)
        self._logger.info(f"connectionRequest: {connectionRequest}, links: {links}")
        bandwidth = connectionRequest.required_bandwidth
        if reduce:
            bandwidth = (-1) * bandwidth
        for link in links:
            p1 = link["source"]
            p2 = link["destination"]
            # update in three places: (1) topology object (2) graph object (3) json to DB
            # (1) topology object
            self.topology_manager.change_link_property_by_value(
                p1, p2, Constants.RESIDUAL_BANDWIDTH, bandwidth
            )

        # (2) graph object, called by sdx-controller
        # self.graph = TESolver.update_graph(self.graph, solution)
        # (3) json to DB, in sdx-controller

    def add_breakdowns_to_connection(self, connection_request: dict, breakdowns: dict):
        """
        add breakdowns to connection request for the sdx-controller to process.
        """
        connection_request["breakdowns"] = breakdowns

        return connection_request

    def generate_connection_breakdown(
        self, solution: ConnectionSolution, connection_request: dict
    ) -> dict:
        """
        Take a connection solution and generate a breakdown.

        A connection solution has a possible path between the
        requested source and destination ports, but no VLANs have been
        assigned yet.  We assign ports in this step.
        """
        if solution is None or solution.connection_map is None:
            self._logger.warning(f"Can't find a TE solution for {connection_request}")
            raise TEError(f"Can't find a TE solution for: {connection_request}", 410)

        breakdown = {}
        paths = solution.connection_map  # p2p for now

        for domain, links in paths.items():
            self._logger.info(f"domain: {domain}, links: {links}")

            current_link_set = []

            for count, link in enumerate(links):
                self._logger.info(f"count: {count}, link: {link}")

                assert isinstance(link, ConnectionPath)

                src_node = self.graph.nodes.get(link.source)
                assert src_node is not None

                dst_node = self.graph.nodes.get(link.destination)
                assert dst_node is not None

                self._logger.info(
                    f"source node: {src_node}, destination node: {dst_node}"
                )

                src_domain = self.topology_manager.get_domain_name(src_node["id"])
                dst_domain = self.topology_manager.get_domain_name(dst_node["id"])

                # TODO: what do we do when a domain can't be
                # determined? Can a domain be `None`?
                self._logger.info(
                    f"source domain: {src_domain}, destination domain: {dst_domain}"
                )

                current_link_set.append(link)
                current_domain = src_domain
                if src_domain == dst_domain:
                    # current_domain = domain_1
                    if count == len(links) - 1:
                        breakdown[current_domain] = current_link_set.copy()
                else:
                    breakdown[current_domain] = current_link_set.copy()
                    if count == len(links) - 1:
                        current_link_set = []
                        current_link_set.append(link)
                        breakdown[dst_domain] = current_link_set.copy()
                    current_domain = None
                    current_link_set = []

        self._logger.info(f"[intermediate] breakdown: {breakdown}")

        # now starting with the ingress_port
        first = True
        i = 0
        domain_breakdown = {}

        # TODO: using dict to represent a breakdown is dubious, and
        # may lead to incorrect results.  Dicts are lexically ordered,
        # and that may break some assumptions about the order in which
        # we form and traverse the breakdown.

        # Note: Extra flag to indicate if the connection request is in
        # the format of TrafficMatrix or not.
        #
        # If the connection request is in the format of TrafficMatrix,
        # then the ingress_port and egress_port are not present in the
        # connection_request
        request_format_is_tm = isinstance(connection_request, list)
        self._logger.info(
            f"connection_request: {connection_request}; "
            f"type: {'tm' if request_format_is_tm else 'not tm'}"
        )
        same_domain_port_flag = False
        if not request_format_is_tm:
            connection_request = (
                ConnectionHandler().import_connection_data(connection_request).to_dict()
            )
            self._logger.info(
                f'connection_request ingress_port: {connection_request["ingress_port"]["id"]}'
            )
            self._logger.info(
                f'connection_request egress_port: {connection_request["egress_port"]["id"]}'
            )
            # flag to indicate if the request ingress and egress ports
            # belong to the same domain.
            same_domain_port_flag = self.topology_manager.are_two_ports_same_domain(
                connection_request["ingress_port"]["id"],
                connection_request["egress_port"]["id"],
            )
            self._logger.info(f"same_domain_user_port_flag: {same_domain_port_flag}")

        # Now generate the breakdown with potential user specified tags
        ingress_user_port = None
        egress_user_port = None

        if not request_format_is_tm:
            ingress_user_port = connection_request.get("ingress_port")
            egress_user_port = connection_request.get("egress_port")

        for domain, links in breakdown.items():
            self._logger.debug(
                f"Creating domain_breakdown: domain: {domain}, links: {links}"
            )
            segment = {}

            if first:
                first = False
                # ingress port for this domain is on the first link.
                if (
                    not request_format_is_tm
                    and connection_request["ingress_port"]["id"]
                    not in self.topology_manager.get_port_link_map()
                ):
                    self._logger.warning(
                        f"Port {connection_request['ingress_port']['id']} not found in port map, it's a user port"
                    )
                    ingress_port_id = connection_request["ingress_port"]["id"]
                    ingress_port = self.topology_manager.get_port_by_id(ingress_port_id)
                else:
                    if request_format_is_tm:
                        ingress_port, _ = self._get_ports_by_link(links[0])
                    else:
                        ingress_port = self.topology_manager.get_port_by_id(
                            connection_request["ingress_port"]["id"]
                        )

                # egress port for this domain is on the last link.
                if (
                    not request_format_is_tm
                    and same_domain_port_flag
                    and connection_request["egress_port"]["id"]
                    not in self.topology_manager.get_port_link_map()
                ):
                    self._logger.warning(
                        f"Port {connection_request['egress_port']['id']} not found in port map, it's a user port"
                    )
                    egress_port_id = connection_request["egress_port"]["id"]
                    egress_port = self.topology_manager.get_port_by_id(egress_port_id)
                    _, next_ingress_port = self._get_ports_by_link(links[-1])
                else:
                    egress_port, next_ingress_port = self._get_ports_by_link(links[-1])
                    if same_domain_port_flag:
                        egress_port = next_ingress_port
                self._logger.info(
                    f"ingress_port:{ingress_port}, egress_port:{egress_port}, next_ingress_port:{next_ingress_port}"
                )
            elif i == len(breakdown) - 1:
                ingress_port = next_ingress_port
                if (
                    not request_format_is_tm
                    and connection_request["egress_port"]["id"]
                    not in self.topology_manager.get_port_link_map()
                ):
                    self._logger.warning(
                        f"Port {connection_request['egress_port']['id']} not found in port map, it's a user port"
                    )
                    egress_port_id = connection_request["egress_port"]["id"]
                    egress_user_port = connection_request["egress_port"]
                    egress_port = self.topology_manager.get_port_by_id(egress_port_id)
                else:
                    _, egress_port = self._get_ports_by_link(links[-1])

                self._logger.info(f"links[-1]: {links[-1]}")
                self._logger.info(
                    f"ingress_port:{ingress_port}, egress_port:{egress_port}"
                )
            else:
                ingress_port = next_ingress_port
                egress_port, next_ingress_port = self._get_ports_by_link(links[-1])

            segment = {}
            segment["ingress_port"] = ingress_port
            segment["egress_port"] = egress_port

            self._logger.info(f"segment for {domain}: {segment}")

            domain_breakdown[domain] = segment.copy()
            i = i + 1

        self._logger.info(
            f"generate_connection_breakdown(): domain_breakdown: {domain_breakdown} "
            f"ingress_user_port: {ingress_user_port}, "
            f"egress_user_port: {egress_user_port}"
        )

        tagged_breakdown = self._reserve_vlan_breakdown(
            domain_breakdown=domain_breakdown,
            request_id=solution.request_id,
            ingress_user_port=ingress_user_port,
            egress_user_port=egress_user_port,
        )
        self._logger.info(
            f"generate_connection_breakdown(): tagged_breakdown: {tagged_breakdown}"
        )

        # Make tests pass, temporarily.
        # ToDo: need to throw an exception if tagged_breakdown is None
        if tagged_breakdown is None:
            raise TEError(
                f"Can't find a valid vlan breakdown solution for: {connection_request}",
                409,
            )

        assert isinstance(tagged_breakdown, VlanTaggedBreakdowns)

        # Now it is the time to update the bandwidth of the links after breakdowns are successfully generated
        self.update_link_bandwidth(solution, reduce=True)

        # keep the connection solution for future reference
        self._connectionSolution_list.append(solution)

        # Return a dict containing VLAN-tagged breakdown in the
        # expected format.
        return tagged_breakdown.to_dict().get("breakdowns")

    def _get_ports_by_link(self, link: ConnectionPath):
        """
        Given a link, find the ports associated with it.

        Returns a (Port, Port) tuple.
        """
        assert isinstance(link, ConnectionPath)

        node1 = self.graph.nodes[link.source]["id"]
        node2 = self.graph.nodes[link.destination]["id"]

        ports = self.topology_manager.get_topology().get_port_by_link(node1, node2)

        # Avoid some possible crashes.
        if ports is None:
            return None, None

        n1, p1, n2, p2 = ports

        assert n1 == node1
        assert n2 == node2

        return p1, p2

    """
    functions for vlan reservation.

    Operations are:

        - obtain the available vlan lists

        - find the vlan continuity on a path if possible.

        - find the vlan translation on the multi-domain path if
          continuity not possible

        - reserve the vlan on all the ports on the path

        - unreserve the vlan when the path is removed
    """

    def _reserve_vlan_breakdown(
        self,
        domain_breakdown: dict,
        request_id: str,
        ingress_user_port=None,
        egress_user_port=None,
    ) -> Optional[VlanTaggedBreakdowns]:
        """
        Upate domain breakdown with VLAN reservation information.

        This is the top-level function, to be called after
        _generate_connection_breakdown_tm(), and should be a private
        implementation detail.  It should be always called, meaning,
        the VLAN tags should be present in the final breakdown,
        regardless of whether the connection request explicitly asked
        for it or not.

        For this to work, TEManager should maintain a table of VLAN
        allocation from each of the domains.  The ones that are not in
        use can be reserved, and the ones that are not in use anymore
        should be returned to the pool by calling unreserve().

        :param domain_breakdown: per port available vlan range is
            pased in datamodel._parse_available_vlans(self, vlan_str)

        :return: Updated domain_breakdown with the VLAN assigned to
                 each port along a path, or None if failure.
        """

        # # Check if there exist a path of vlan continuity.  This is
        # # disabled for now, until the simple case is handled.
        # selected_vlan = self.find_vlan_on_path(domain_breakdown)
        # if selected_vlan is not None:
        #     return self._reserve_vlan_on_path(domain_breakdown, selected_vlan)

        # if not, assuming vlan translation on the domain border port

        self._logger.info(
            f"reserve_vlan_breakdown: domain_breakdown: {domain_breakdown}"
        )

        domain_breakdown_list = list(domain_breakdown.items())
        domain_breakdown_list_len = len(domain_breakdown_list)
        common_vlan_on_link = {}  # {domain1: upstream_egress_vlan}
        for i in range(domain_breakdown_list_len - 1):
            domain, segment = domain_breakdown_list[i]
            next_domain, next_segment = domain_breakdown_list[i + 1]
            self._logger.info(
                f"Find a common vlan: domain: {domain}, segment: {segment}, next_domain: {next_domain}, next_segment: {next_segment}"
            )

            upstream_egress = segment.get("egress_port")
            downstream_ingress = next_segment.get("ingress_port")
            upstream_egress_vlan = self._find_common_vlan_on_link(
                domain, upstream_egress["id"], next_domain, downstream_ingress["id"]
            )
            self._logger.info(
                f"upstream_egress_vlan: {upstream_egress_vlan}; upstream_egress: {upstream_egress}; downstream_ingress: {downstream_ingress}"
            )
            if upstream_egress_vlan is None:
                return (
                    None,
                    f"Failed: No common VLAN found on the link:{upstream_egress['id']} -> {downstream_ingress['id']}",
                )
            common_vlan_on_link[domain] = upstream_egress_vlan

        breakdowns = {}
        i = 0
        upstream_egress_vlan = None
        downstream_ingress_vlan = None
        for domain, segment in domain_breakdown.items():
            # These are topology ports
            ingress_port = segment.get("ingress_port")
            egress_port = segment.get("egress_port")

            if ingress_port is None or egress_port is None:
                return None
            ingress_user_port_tag = None
            egress_user_port_tag = None
            if (
                ingress_user_port is not None
                and ingress_port["id"] == ingress_user_port["id"]
            ):
                ingress_user_port_tag = ingress_user_port.get("vlan_range")
            if (
                egress_user_port is not None
                and egress_port["id"] == egress_user_port["id"]
            ):
                egress_user_port_tag = egress_user_port.get("vlan_range")

            self._logger.info(
                f"VLAN reservation: domain: {domain}, "
                f"ingress_port: {ingress_port}, egress_port: {egress_port},"
                f"ingress_user_port_tag: {ingress_user_port_tag}, egress_user_port_tag: {egress_user_port_tag},"
                f"upstream_egress_vlan: {upstream_egress_vlan}"
            )

            if i == 0:  # first domain
                upstream_egress_vlan = None
                downstream_ingress_vlan = common_vlan_on_link.get(domain)
            elif i == domain_breakdown_list_len - 1:  # last domain
                downstream_ingress_vlan = None
            else:  # middle domain
                downstream_ingress_vlan = common_vlan_on_link.get(domain)

            i += 1

            ingress_vlan = self._reserve_vlan(
                domain,
                ingress_port,
                request_id,
                ingress_user_port_tag,
                upstream_egress_vlan,
            )
            egress_vlan = self._reserve_vlan(
                domain,
                egress_port,
                request_id,
                egress_user_port_tag,
                downstream_ingress_vlan,
            )

            if ingress_vlan is None or egress_vlan is None:
                self._logger.error(
                    f"ingress_vlan: {ingress_vlan}, egress_vlan: {egress_vlan}. "
                    f"Can't proceed. Rolling back reservations."
                )
                self.unreserve_vlan(request_id=request_id)
                return None

            ingress_port_id = ingress_port["id"]
            egress_port_id = egress_port["id"]

            upstream_egress_vlan = egress_vlan

            # TODO: what to do when a port is not in the port map
            # which only has all the ports on links?
            #
            # User facing ports need clarification from the
            # custermers.  For now, we are assuming that the user
            # facing port either (1) provides the vlan or (2) uses the
            # OXP vlan if (2.1) not provided or provided (2.2) is not
            # in the vlan range in the topology port.  And we do't
            # allow user specified vlan on a OXP port.
            if (
                ingress_port_id not in self.topology_manager.get_port_link_map()
                and ingress_vlan is None
            ):
                self._logger.warning(
                    f"Port {ingress_port_id} not found in port map, it's a user port, by default uses the OXP vlan"
                )
                ingress_vlan = egress_vlan

            if (
                egress_port_id not in self.topology_manager.get_port_link_map()
                and egress_vlan is None
            ):
                self._logger.warning(
                    f"Port {egress_port_id} not found in port map, it's a user port, by default uses the OXP vlan"
                )
                egress_vlan = ingress_vlan

            self._logger.info(
                f"VLAN reservation: domain: {domain}, "
                f"ingress_vlan: {ingress_vlan}, egress_vlan: {egress_vlan}"
            )

            # # vlan translation from upstream_o_vlan to i_vlan
            # segment["ingress_upstream_vlan"] = upstream_o_vlan
            # segment["ingress_vlan"] = ingress_vlan
            # segment["egress_vlan"] = egress_vlan
            # upstream_o_vlan = egress_vlan

            port_a = VlanTaggedPort(
                VlanTag(value=ingress_vlan, tag_type=1), port_id=ingress_port_id
            )
            port_z = VlanTaggedPort(
                VlanTag(value=egress_vlan, tag_type=1), port_id=egress_port_id
            )

            # Names look like "AMLIGHT_vlan_201_202_Ampath_Tenet".  We
            # can form the initial part, but where did the
            # `Ampath_Tenet` at the end come from?
            domain_name = domain.split(":")[-1].split(".")[0].upper()
            name = f"{domain_name}_vlan_{ingress_vlan}_{egress_vlan}"

            breakdowns[domain] = VlanTaggedBreakdown(
                name=name,
                dynamic_backup_path=True,
                uni_a=port_a,
                uni_z=port_z,
            )

        return VlanTaggedBreakdowns(breakdowns=breakdowns)

    def _find_vlan_on_path(self, path):
        """
        Find an unused available VLAN on path.

        Finds a VLAN that's not being used at the moment on a provided
        path.  Returns an available VLAN if possible, None if none are
        available on the submitted path.

        output: vlan_tag string or None
        """

        # TODO: implement this
        # https://github.com/atlanticwave-sdx/pce/issues/126

        assert False, "Not implemented"

    def _reserve_vlan_on_path(self, domain_breakdown, selected_vlan):
        # TODO: what is the difference between reserve_vlan and
        # reserve_vlan_on_path?

        # TODO: implement this
        # https://github.com/atlanticwave-sdx/pce/issues/126

        # return domain_breakdown
        assert False, "Not implemented"

    def _find_common_vlan_on_link(
        self, domain, upstream_egress, next_domain, downstream_ingress
    ) -> Optional[str]:
        """
        Find a common VLAN on the inter-domain link.

        This function is used to find a common VLAN on the inter-domain link.
        """
        upstream_vlan_table = self._vlan_tags_table.get(domain).get(upstream_egress)
        downstream_vlan_table = self._vlan_tags_table.get(next_domain).get(
            downstream_ingress
        )

        if upstream_vlan_table is None or downstream_vlan_table is None:
            self._logger.error(f"Can't find VLAN tables for {domain} and {next_domain}")
            return None
        common_vlans = set(upstream_vlan_table.keys()).intersection(
            downstream_vlan_table.keys()
        )

        for vlan in common_vlans:
            if (
                upstream_vlan_table[vlan] is UNUSED_VLAN
                and downstream_vlan_table[vlan] is UNUSED_VLAN
            ):
                return vlan

        self._logger.warning(
            f"No common VLAN found between {domain} and {next_domain} for ports {upstream_egress} and {downstream_ingress}"
        )
        return None

    def _reserve_vlan(
        self,
        domain: str,
        port: dict,
        request_id: str,
        tag: str = None,
        upstream_egress_vlan: str = None,
    ):
        """
        Find unused VLANs for given domain/port and mark them in-use.

        :param domain: a string that contains the domain.
        :param port: a `dict` that represents a port.
        :param request_id: a string that contains the request ID.
        :param tag: a string that is used to specify VLAN tag
            preferences.  None or "any" means that any available VLAN
            will do.  A number or range will indicate a specific
            demand; "all" and "untagged" will indicate other
            preferences.  See the description of "vlan" under
            "Mandatory Attributes" section of the Service Provisioning
            Data Model Specification 1.0 for details.
        :param upstream_vlan: a string that contains the upstream tag to use

            https://sdx-docs.readthedocs.io/en/latest/specs/provisioning-api-1.0.html#mandatory-attributes
        """

        # with self._topology_lock:
        #     pass

        self._logger.debug(
            f"Reserving VLAN for domain: {domain}, port: {port}, "
            f"request_id: {request_id}, tag:{tag}"
        )

        # Look up available VLAN tags by domain and port ID.
        # self._logger.debug(f"vlan tags table: {self._vlan_tags_table}")
        domain_table = self._vlan_tags_table.get(domain)

        if domain_table is None:
            self._logger.error(f"reserve_vlan domain: {domain} entry: {domain_table}")
            return None

        port_id = port.get("id")
        if port_id is None:
            self._logger.error("port_id is None; giving up")
            return None

        vlan_table = domain_table.get(port_id)

        self._logger.debug(f"reserve_vlan domain: {domain} vlan_table: {vlan_table}")

        if vlan_table is None:
            self._logger.warning(
                f"Can't find a VLAN table for domain: {domain} port: {port_id}"
            )
            return None

        if tag is None:
            tag = upstream_egress_vlan
            self._logger.info(f"tag is None, using the upstream_egress_vlan: {tag}")
        else:
            self._logger.info(f"tag is not None, using the tag: {tag}")

        if tag in (None, "any"):
            # Find the first available VLAN tag from the table.
            for vlan_tag, vlan_usage in vlan_table.items():
                if vlan_usage is UNUSED_VLAN:
                    available_tag = vlan_tag
        else:
            if tag in vlan_table:
                if vlan_table[tag] is UNUSED_VLAN:
                    self._logger.debug(f"VLAN {tag} is available; marking as in-use")
                    available_tag = tag
                else:
                    self._logger.error(f"VLAN {tag} is in use by {vlan_table[tag]}")
                    return None
            else:
                self._logger.error(f"VLAN {tag} is not present in the table")
                return None

        # mark the tag as in-use.
        vlan_table[available_tag] = request_id

        self._logger.debug(
            f"reserve_vlan domain {domain}, after reservation: "
            f"vlan_table: {vlan_table}, available_tag: {available_tag}"
        )

        return available_tag

    def unreserve_vlan(self, request_id: str):
        """
        Return previously reserved VLANs back to the pool.
        """
        found_assignment = False

        for domain, port_table in self._vlan_tags_table.items():
            for port, vlan_table in port_table.items():
                for vlan, assignment in vlan_table.items():
                    if assignment == request_id:
                        vlan_table[vlan] = UNUSED_VLAN
                        found_assignment = True

        # We should let the invoker know that we could not find the
        # request ID.
        if not found_assignment:
            raise UnknownRequestError(
                "Unknown connection request", request_id=request_id
            )

    def delete_connection(self, request_id: str):
        """
        Delete a connection.

        This function is used to delete a connection.  It will
        unreserve the VLANs that were reserved for the connection.
        """
        self.unreserve_vlan(request_id)
        solution = self.get_connection_solution(request_id)
        if solution is None:
            self._logger.warning(f"Can't find a solution for request ID {request_id}")
            return None

        # Remove the solution from the list.
        self._connectionSolution_list.remove(solution)
        # Now it is the time to update the bandwidth of the links after breakdowns are successfully generated
        self.update_link_bandwidth(solution, reduce=False)

    def get_connection_solution(self, request_id: str) -> ConnectionSolution:
        """
        Get a connection solution by request ID.
        """
        for solution in self._connectionSolution_list:
            if solution.request_id == request_id:
                return solution

        return None

    def _print_vlan_tags_table(self):
        """
        Occasionally useful when debugguing.
        """
        import pprint

        self._logger.info("------ VLAN TAGS TABLE -------")
        self._logger.info(pprint.pformat(self._vlan_tags_table))
        self._logger.info("------------------------------")
