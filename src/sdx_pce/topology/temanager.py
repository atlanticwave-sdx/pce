import threading
from itertools import chain
from typing import List, Optional

import networkx as nx
from networkx.algorithms import approximation as approx
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
from sdx_pce.utils.exceptions import ValidationError


class TEManager:

    """
    TE Manager for connection - topology operations.

    Functions of this class are:

        - generate inputs to the PCE solver

        - converter the solver output.

        - VLAN reservation and unreservation.
    """

    def __init__(self, topology_data):
        super().__init__()

        self.topology_manager = TopologyManager()

        # A lock to safely perform topology operations.
        self._topology_lock = threading.Lock()

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

        # TODO: careful here when updating VLAN tags table -- what do
        # we do when an in use VLAN tag becomes invalid in the update?
        # See https://github.com/atlanticwave-sdx/pce/issues/123
        #
        # self._update_vlan_tags_table_from_links(
        #     domain_name=topology_data.get("id"),
        #     port_list=self.topology_manager.port_list,
        # )

    def _update_vlan_tags_table(self, domain_name: str, port_map: dict):
        """
        Update VLAN tags table.
        """
        self._vlan_tags_table[domain_name] = {}

        for port_id, link in port_map.items():
            # TODO: port here seems to be a dict, not sdx_datamodel.models.Port
            for port in link.ports:
                # Collect all port IDs in this link.  Each link should
                # have two ports.
                link_port_ids = [x.get("id") for x in link.ports]

                # Do some error checks.
                link_port_count = len(link_port_ids)

                if link_port_count != 2:
                    raise ValidationError(f"Link has {link_port_count} ports, not 2")

                if port_id not in link_port_ids:
                    raise ValidationError(f"port {port_id} not in {link_port_ids}")

                label_range = port.get("label_range")

                # TODO: why is label_range sometimes None, and what to
                # do when that happens?
                if label_range is None:
                    print(f"label_range on {port.get('id')} is None")
                    continue

                # label_range is of the form ['100-200', '1000']; let
                # us expand it.  Would have been ideal if this was
                # already in some parsed form, but it is not, so this
                # is a work-around.
                all_labels = self._expand_label_range(label_range)

                # Make a map lik: `{tag1: True, tag2: True, tag3: True...}`
                labels_available = {label: True for label in all_labels}

                self._vlan_tags_table[domain_name][port_id] = labels_available

    def _expand_label_range(self, label_range: List[str]) -> List[int]:
        """
        Expand the label range to a list of numbers.
        """
        labels = [self._expand_label(label) for label in label_range]
        # flatten result and return it.
        return list(chain.from_iterable(labels))

    def _expand_label(self, label: str) -> List[int]:
        """
        Expand items in label range to a list of numbers.

        Items in label ranges can be of the form "100-200" or "100".
        For the first case, we return [100,101,...200]; for the second
        case, we return [100].
        """
        if not isinstance(label, str):
            raise ValidationError("Label must be a string.")

        parts = label.split("-")
        start = int(parts[0])
        stop = int(parts[-1]) + 1

        return list(range(start, stop))

    def generate_connection_te(self, connection_request: dict) -> TrafficMatrix:
        """
        Generate a Traffic Matrix from the connection request we have.
        """
        print(f"generate_connection_te: connection_request: {connection_request}")

        request = ConnectionHandler().import_connection_data(connection_request)

        print(f"generate_connection_te: decoded request: {request}")

        ingress_port = request.ingress_port
        egress_port = request.egress_port

        print(
            f"generate_connection_te(), ports: "
            f"ingress_port.id: {ingress_port.id}, "
            f"egress_port.id: {egress_port.id}"
        )

        topology = self.topology_manager.get_topology()

        ingress_node = topology.get_node_by_port(ingress_port.id)
        egress_node = topology.get_node_by_port(egress_port.id)

        if ingress_node is None:
            print(f"No ingress node was found for ingress port ID '{ingress_port.id}'")
            return None

        if egress_node is None:
            print(f"No egress node is found for egress port ID '{egress_port.id}'")
            return None

        ingress_nodes = [
            x for x, y in self.graph.nodes(data=True) if y["id"] == ingress_node.id
        ]

        egress_nodes = [
            x for x, y in self.graph.nodes(data=True) if y["id"] == egress_node.id
        ]

        if len(ingress_nodes) <= 0:
            print(f"No ingress node '{ingress_node.id}' found in the graph")
            return None

        if len(egress_nodes) <= 0:
            print(f"No egress node '{egress_node.id}' found in the graph")
            return None

        required_bandwidth = request.bandwidth or 0
        required_latency = request.latency or 0

        print(
            f"Setting required_latency: {required_latency}, "
            f"required_bandwidth: {required_bandwidth}"
        )

        request = ConnectionRequest(
            source=ingress_nodes[0],
            destination=egress_nodes[0],
            required_bandwidth=required_bandwidth,
            required_latency=required_latency,
        )

        return TrafficMatrix(connection_requests=[request])

    def generate_graph_te(self) -> nx.Graph:
        """
        Return the topology graph that we have.
        """
        graph = self.topology_manager.generate_graph()
        graph = nx.convert_node_labels_to_integers(graph, label_attribute="id")

        # TODO: why is this needed?
        self.graph = graph
        # print(list(graph.nodes(data=True)))

        return graph

    def graph_node_connectivity(self, source=None, dest=None):
        """
        Check that a source and destination node have connectivity.
        """
        # TODO: is this method really needed?
        return approx.node_connectivity(self.graph, source, dest)

    def requests_connectivity(self, tm: TrafficMatrix) -> bool:
        """
        Check that connectivity is possible.
        """
        # TODO: consider using filter() and reduce(), maybe?
        # TODO: write some tests for this method.
        for request in tm.connection_requests:
            conn = self.graph_node_connectivity(request.source, request.destination)
            print(
                f"Request connectivity: source {request.source}, destination: {request.destination} = {conn}"
            )
            if conn is False:
                return False

        return True

    def generate_connection_breakdown(self, solution: ConnectionSolution) -> dict:
        """
        Take a connection solution and generate a breakdown.

        This is an alternative to generate_connection_breakdown()
        below which uses the newly defined types from sdx_pce.models.
        """
        if solution is None or solution.connection_map is None:
            print(f"Can't find a breakdown for {solution}")
            return None

        breakdown = {}
        paths = solution.connection_map  # p2p for now

        for domain, links in paths.items():
            print(f"domain: {domain}, links: {links}")

            current_link_set = []

            for count, link in enumerate(links):
                print(f"count: {count}, link: {link}")

                assert isinstance(link, ConnectionPath)

                src_node = self.graph.nodes.get(link.source)
                assert src_node is not None

                dst_node = self.graph.nodes.get(link.destination)
                assert dst_node is not None

                print(f"source node: {src_node}, destination node: {dst_node}")

                src_domain = self.topology_manager.get_domain_name(src_node.get("id"))
                dst_domain = self.topology_manager.get_domain_name(dst_node.get("id"))

                # TODO: what do we do when a domain can't be
                # determined? Can a domain be `None`?
                print(f"source domain: {src_domain}, destination domain: {dst_domain}")

                current_link_set.append(link)
                current_domain = src_domain
                if src_domain == dst_domain:
                    # current_domain = domain_1
                    if count == len(links) - 1:
                        breakdown[current_domain] = current_link_set.copy()
                else:
                    breakdown[current_domain] = current_link_set.copy()
                    current_domain = None
                    current_link_set = []

        print(f"[intermediate] breakdown: {breakdown}")

        # now starting with the ingress_port
        first = True
        i = 0
        domain_breakdown = {}

        for domain, links in breakdown.items():
            print(f"Creating domain_breakdown: domain: {domain}, links: {links}")
            segment = {}
            if first:
                first = False

                first_link = links[0]
                first_link_node1 = self.graph.nodes[first_link.source]["id"]
                first_link_node2 = self.graph.nodes[first_link.destination]["id"]
                (
                    _,
                    first_link_port1,
                    _,
                    _,
                ) = self.topology_manager.get_topology().get_port_by_link(
                    first_link_node1, first_link_node2
                )
                print(f"First link, domain: {domain}, port1: {first_link_port1}")
                i_port = first_link_port1

                last_link = links[-1]
                n1 = self.graph.nodes[last_link.source]["id"]
                n2 = self.graph.nodes[last_link.destination]["id"]
                n1, p1, n2, p2 = self.topology_manager.get_topology().get_port_by_link(
                    n1, n2
                )
                print(
                    f"Last link, domain: {domain}, n1 => {n1}, p1 => {p1}, n2 => {n2}, p2 => {p2}"
                )
                e_port = p1
                next_i = p2
            elif i == len(breakdown) - 1:
                i_port = next_i
                # e_port = self.connection.egress_port.to_dict()
                link = links[i]
                n1 = self.graph.nodes[link.source]["id"]
                n2 = self.graph.nodes[link.destination]["id"]
                n1, p1, n2, p2 = self.topology_manager.get_topology().get_port_by_link(
                    n1, n2
                )
                print(
                    f"Link #{i}, domain: {domain}, n1 => {n1}, p1 => {p1}, n2 => {n2}, p2 => {p2}"
                )
                e_port = p2
                
            else:
                last_link = links[-1]
                n1 = self.graph.nodes[last_link.source]["id"]
                n2 = self.graph.nodes[last_link.destination]["id"]
                n1, p1, n2, p2 = self.topology_manager.get_topology().get_port_by_link(
                    n1, n2
                )
                i_port = next_i
                e_port = p1
                next_i = p2
            segment["ingress_port"] = i_port
            segment["egress_port"] = e_port
            domain_breakdown[domain] = segment.copy()
            i = i + 1

        print(f"generate_connection_breakdown(): domain_breakdown: {domain_breakdown}")

        tagged_breakdown = self._reserve_vlan_breakdown(domain_breakdown)
        print(f"generate_connection_breakdown(): tagged_breakdown: {tagged_breakdown}")

        # Make tests pass, temporarily.
        if tagged_breakdown is None:
            return None

        assert isinstance(tagged_breakdown, VlanTaggedBreakdowns)

        # Return a dict containing VLAN-tagged breakdown in the
        # expected format.
        return tagged_breakdown.to_dict().get("breakdowns")

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
        self, domain_breakdown: dict
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

        print(f"reserve_vlan_breakdown: domain_breakdown: {domain_breakdown}")

        breakdowns = {}

        # upstream_o_vlan = ""
        for domain, segment in domain_breakdown.items():
            ingress_port = segment.get("ingress_port")
            egress_port = segment.get("egress_port")

            print(
                f"VLAN reservation: domain: {domain}, "
                f"ingress_port: {ingress_port}, egress_port: {egress_port}"
            )

            if ingress_port is None or egress_port is None:
                return None

            ingress_vlan = self._reserve_vlan(domain, ingress_port)
            egress_vlan = self._reserve_vlan(domain, egress_port)

            ingress_port_id = ingress_port.get("id")
            egress_port_id = egress_port.get("id")

            print(
                f"VLAN reservation: domain: {domain}, "
                f"ingress_vlan: {ingress_vlan}, egress_vlan: {egress_vlan}"
            )

            # if one has empty vlan range, first resume reserved vlans
            # in the previous domain, then return false.
            if egress_vlan is None:
                self._unreserve_vlan(ingress_vlan)
                return None

            if ingress_vlan is None:
                self._unreserve_vlan(egress_vlan)
                return None

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

    def _reserve_vlan(self, domain: str, port: dict, tag=None):
        # with self._topology_lock:
        #     pass

        port_id = port.get("id")
        print(f"reserve_vlan domain: {domain} port_id: {port_id}")

        if port_id is None:
            return None

        # Look up available VLAN tags by domain and port ID.
        domain_table = self._vlan_tags_table.get(domain)

        if domain_table is None:
            print(f"reserve_vlan domain: {domain} entry: {domain_table}")
            return None

        vlan_table = domain_table.get(port_id)

        print(f"reserve_vlan domain: {domain} vlan_table: {vlan_table}")

        # TODO: figure out when vlan_table can be None
        if vlan_table is None:
            print(f"Can't find a mapping for domain:{domain} port:{port_id}")
            return None

        available_tag = None

        if tag is None:
            # Find the first available VLAN tag from the table.
            for vlan_tag, vlan_available in vlan_table.items():
                if vlan_available:
                    available_tag = vlan_tag
        else:
            if vlan_table[tag] is True:
                available_tag = tag
            else:
                return None

        if available_tag is not None:
            # mark the tag as in-use.
            vlan_table[available_tag] = False

        # available_tag = 200
        return available_tag

    # to be called by delete_connection()
    def _unreserve_vlan_breakdown(self, break_down):
        # TODO: implement this.
        # https://github.com/atlanticwave-sdx/pce/issues/127
        # with self._topology_lock:
        #     pass
        assert False, "Not implemented"

    def _unreserve_vlan(self, domain: str, port: dict, tag=None):
        """
        Mark a VLAN tag as not in use.
        """
        # TODO: implement this.
        # https://github.com/atlanticwave-sdx/pce/issues/127

        # with self._topology_lock:
        #     pass
        assert False, "Not implemented"

    def _print_vlan_tags_table(self):
        import pprint

        print("------ VLAN TAGS TABLE -------")
        pprint.pprint(self._vlan_tags_table)
        print("------------------------------")
