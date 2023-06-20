import threading
from typing import Optional, List

import networkx as nx
from networkx.algorithms import approximation as approx

from sdx.datamodel.parsing.connectionhandler import ConnectionHandler
from sdx.pce.models import (
    ConnectionPath,
    ConnectionRequest,
    ConnectionSolution,
    TaggedBreakdown,
    TaggedPort,
    TrafficMatrix,
    VLANTag,
)
from sdx.pce.topology.manager import TopologyManager


class TEManager:

    """
    TE Manager for connection - topology operations.

    Functions of this class are:

        - generate inputs to the PCE solver

        - converter the solver output.

        - VLAN reservation and unreservation.
    """

    def __init__(self, topology_data, connection_data):
        super().__init__()

        self.topology_manager = TopologyManager()
        self.connection_handler = ConnectionHandler()

        # Making topology_data optional while investigating
        # https://github.com/atlanticwave-sdx/sdx-controller/issues/145.
        # TODO: a nicer thing to do would be to keep less state around.
        if topology_data:
            self.topology_manager.add_topology(topology_data)
            self.graph = self.generate_graph_te()
        else:
            self.graph = None

        print(f"TEManager: connection_data: {connection_data}")

        self.connection = self.connection_handler.import_connection_data(
            connection_data
        )

        print(f"TEManager: self.connection: {self.connection}")

        self.topology_lock = threading.Lock()

        # A {domain, {port, {vlan, in_use}}} mapping.
        self._vlan_tags_table = {}

    def add_topology(self, topology_data: dict):
        """
        Add a new topology to TEManager.

        :param topology_data: a dictionary that represents a topology.
        """
        self.topology_manager.add_topology(topology_data)

        domain_name = topology_data.get("id")

        nodes = self.topology_manager.topology.nodes
        self._update_vlan_tags_table_from_nodes(domain_name, nodes)

        # self._update_vlan_tags_table_from_links(domain_name, self.topology_manager.port_list)

    def update_topology(self, topology_data: dict):
        """
        Update an existing topology in TEManager.

        :param topology_data: a dictionary that represents a topology.
        """
        self.topology_manager.update_topology(topology_data)

        ## TODO: careful here when updating VLAN tags table -- what do
        ## we do when an in use VLAN tag becomes invalid in the update?
        # self._update_vlan_tags_table_from_nodes(self.topology_manager.topology.nodes)

    def _update_vlan_tags_table_from_nodes(self, domain_name: str, nodes):
        """
        VLAN tags availability table from nodes->ports->label_range

        :param domain_name: the domain name
        :param nodes: a list of Node objects.
        """
        for node in nodes:
            port_mapping = {}

            for port in node.ports:
                port_id = port.id

                port_mapping[port_id] = {}

                label_range = port.label_range
                for label in label_range:
                    labels = self._expand_label(label)

                    for label in labels:
                        port_mapping[port_id][label] = True

        self._vlan_tags_table[domain_name] = port_mapping

        # import pprint
        # print("------ VLAN TAGS TABLE -------")
        # pprint.pprint(self._vlan_tags_table)
        # print("------------------------------")

    def _update_vlan_tags_table_from_links(self, domain_name, port_list):
        """
        The version that uses links->ports.

        Also probably the wrong one.
        """
        self._vlan_tags_table[domain_name] = {}

        for port_id, link in port_list.items():
            # TODO: port here seems to be a dict, not sdx.datamodel.models.Port
            for port in link.ports:
                port_id = port.get("id")
                label_range = port.get("label_range")

                assert label_range is not None, "label_range is None"

                # label_range is of the form ['100-200', '1000']; let
                # us expand it.  Would have been ideal if this was
                # already in some parsed form, but it is not, so this
                # is a work-around.
                for label in label_range:
                    labels = self._expand_label(label)
                    labels_available = {}
                    for label in labels:
                        labels_available[label] = True

                self._vlan_tags_table[domain_name][port_id] = labels_available

    def _expand_label(self, label: str) -> List[int]:
        """
        Expand label ranges to a list of numbers.

        Items in label ranges can be of the form "100-200" or "100".
        For the first case, we return [100,101,...200]; for the second
        case, we return [100].
        """
        assert isinstance(label, str)

        labels = label.split("-")
        if len(labels) == 2:
            start = int(labels[0])
            stop = int(labels[1]) + 1
        else:
            start = int(labels[0])
            stop = int(labels[0]) + 1

        assert start < stop

        return list(range(start, stop))

    def generate_connection_te(self) -> TrafficMatrix:
        """
        Generate a Traffic Matrix from the connection request we have.
        """
        ingress_port = self.connection.ingress_port
        egress_port = self.connection.egress_port

        print(
            f"generate_connection_te(), ports: "
            f"ingress_port.id: {ingress_port.id}, "
            f"egress_port.id: {egress_port.id}"
        )

        ingress_node = self.topology_manager.topology.get_node_by_port(ingress_port.id)
        egress_node = self.topology_manager.topology.get_node_by_port(egress_port.id)

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

        required_bandwidth = self.connection.bandwidth or 0
        required_latency = self.connection.latency or 0

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

    def generate_connection_breakdown(self, connection) -> dict:
        """
        A "router" method for backward compatibility.
        """
        if isinstance(connection, ConnectionSolution):
            return self._generate_connection_breakdown_tm(connection)
        return self._generate_connection_breakdown_old(connection)

    def _generate_connection_breakdown_tm(self, connection: ConnectionSolution) -> dict:
        """
        Take a connection and generate a breakdown.

        This is an alternative to generate_connection_breakdown()
        below which uses the newly defined types from sdx.pce.models.
        """
        if connection is None or connection.connection_map is None:
            print(f"Can't find a breakdown for {connection}")
            return None

        breakdown = {}
        paths = connection.connection_map  # p2p for now

        # i_port = None
        # e_port = None

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
                last_link = links[-1]
                n1 = self.graph.nodes[last_link.source]["id"]
                n2 = self.graph.nodes[last_link.destination]["id"]
                n1, p1, n2, p2 = self.topology_manager.topology.get_port_by_link(n1, n2)
                i_port = self.connection.ingress_port.to_dict()
                e_port = p1
                next_i = p2
            elif i == len(breakdown) - 1:
                i_port = next_i
                e_port = self.connection.egress_port.to_dict()
            else:
                last_link = links[-1]
                n1 = self.graph.nodes[last_link.source]["id"]
                n2 = self.graph.nodes[last_link.destination]["id"]
                n1, p1, n2, p2 = self.topology_manager.topology.get_port_by_link(n1, n2)
                i_port = next_i
                e_port = p1
                next_i = p2
            segment["ingress_port"] = i_port
            segment["egress_port"] = e_port
            domain_breakdown[domain] = segment.copy()
            i = i + 1

        print(f"generate_connection_breakdown(): domain_breakdown: {domain_breakdown}")
        return domain_breakdown

    def _generate_connection_breakdown_old(self, connection):
        """
        Take a connection and generate a breakdown.
        """
        assert connection is not None

        breakdown = {}
        paths = connection[0]  # p2p for now
        # cost = connection[1]
        i_port = None
        e_port = None

        print(f"Domain breakdown with graph: {self.graph}")
        print(f"Graph nodes: {self.graph.nodes}")
        print(f"Graph edges: {self.graph.edges}")

        print(f"Paths: {paths}")

        for i, j in paths.items():
            print(f"i: {i}, j: {j}")
            current_link_set = []
            for count, link in enumerate(j):
                print(f"count: {count}, link: {link}")
                assert len(link) == 2

                node_1 = self.graph.nodes.get(link[0])
                assert node_1 is not None

                node_2 = self.graph.nodes.get(link[1])
                assert node_2 is not None

                print(f"node_1: {node_1}, node_2: {node_2}")

                domain_1 = self.topology_manager.get_domain_name(node_1["id"])
                domain_2 = self.topology_manager.get_domain_name(node_2["id"])

                # # TODO: handle the cases where a domain was not found.
                # if domain_1 is None:
                #     domain_1 = f"domain_{i}"
                # if domain_2 is None:
                #     domain_2 = f"domain_{i}"

                print(f"domain_1: {domain_1}, domain_2: {domain_2}")

                current_link_set.append(link)
                current_domain = domain_1
                if domain_1 == domain_2:
                    # current_domain = domain_1
                    if count == len(j) - 1:
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
                last_link = links[-1]
                n1 = self.graph.nodes[last_link[0]]["id"]
                n2 = self.graph.nodes[last_link[1]]["id"]
                n1, p1, n2, p2 = self.topology_manager.topology.get_port_by_link(n1, n2)
                i_port = self.connection.ingress_port.to_dict()
                e_port = p1
                next_i = p2
            elif i == len(breakdown) - 1:
                i_port = next_i
                e_port = self.connection.egress_port.to_dict()
            else:
                last_link = links[-1]
                n1 = self.graph.nodes[last_link[0]]["id"]
                n2 = self.graph.nodes[last_link[1]]["id"]
                n1, p1, n2, p2 = self.topology_manager.topology.get_port_by_link(n1, n2)
                i_port = next_i
                e_port = p1
                next_i = p2
            segment["ingress_port"] = i_port
            segment["egress_port"] = e_port
            domain_breakdown[domain] = segment.copy()
            i = i + 1

        print(f"generate_connection_breakdown(): domain_breakdown: {domain_breakdown}")
        return domain_breakdown

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

    def reserve_vlan_breakdown(
        self, domain_breakdown: dict
    ) -> Optional[TaggedBreakdown]:
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
        #     return self.reserve_vlan_on_path(domain_breakdown, selected_vlan)

        # if not, assuming vlan translation on the domain border port

        print(f"reserve_vlan_breakdown: domain_breakdown: {domain_breakdown}")

        # TODO: Remove this temporary debug print
        import pprint

        print("------ VLAN TAGS TABLE -------")
        pprint.pprint(self._vlan_tags_table)
        print("------------------------------")

        upstream_o_vlan = ""
        for domain, segment in domain_breakdown.items():
            i_port = segment.get("ingress_port")
            e_port = segment.get("egress_port")

            print(
                f"VLAN reservation: domain: {domain}, i_port: {i_port}, e_port: {e_port}"
            )

            if i_port is None or e_port is None:
                return None

            # TODO: find an available vlan for each port out of its
            # available vlan range.
            i_vlan = self.reserve_vlan(domain, i_port)
            o_vlan = self.reserve_vlan(domain, e_port)

            print(
                f"VLAN reservation: domain: {domain}, i_vlan: {i_vlan}, o_vlan: {o_vlan}"
            )

            if i_vlan is None:
                self.unreserve_vlan(o_vlan)
                return None

            if o_vlan is None:
                self.unreserve_vlan(i_vlan)
                return None

            # if one has empty vlan range, first resume reserved vlans in the previous domain, then return false,
            # vlan translation from upstream_o_vlan to i_vlan
            segment["ingress_upstream_vlan"] = upstream_o_vlan
            segment["ingress_vlan"] = i_vlan
            segment["egress_vlan"] = o_vlan
            upstream_o_vlan = o_vlan

        # return domain_breakdown

        port_a = TaggedPort(
            VLANTag(value=200, tag_type=1), interface_id="interface-id-a"
        )
        port_z = TaggedPort(
            VLANTag(value=200, tag_type=1), interface_id="interface-id-z"
        )

        return TaggedBreakdown(
            name="test-breakdown", dynamic_backup_path=False, uni_a=port_a, uni_z=port_z
        )

    def find_vlan_on_path(self, path):
        """
        Find an unused available VLAN on path.

        Finds a VLAN that's not being used at the moment on a provided
        path.  Returns an available VLAN if possible, None if none are
        available on the submitted path.

        output: vlan_tag string or None
        """

        # TODO: implement this

        return None

    def reserve_vlan_on_path(self, domain_breakdown, selected_vlan):
        # TODO: what is the difference between reserve_vlan and
        # reserve_vlan_on_path?

        # TODO: implement this

        return domain_breakdown

    def reserve_vlan(self, domain: str, port: dict, tag=None):
        # TODO: implement this
        # with self.topology_lock:
        #     pass
        print(
            f"reserve_vlan: {port.get('label_range')}, {type(port.get('label_range'))}"
        )

        # label_range = port.get("label_range")
        # print(f"reserve_vlan: label_range={label_range}")
        # if label_range is None:
        #     # TODO: what can we do when there's no label_range?  Is it
        #     # a bug or an error when label_range is None?  Should we
        #     # do an assert here?
        #     # assert label_range is not None
        #     print(f"label_range={label_range}, failing")

        port_id = port.get("id")
        assert port_id is not None
        print(f"reserve_vlan domain: {domain} port_id: {port_id}")

        # vlan_mapping = self._vlan_tags_table.get(domain).get(port_id)
        vlan_table = self._vlan_tags_table.get(domain).get(port_id)
        # print(f"reserve_vlan table={table}")

        # vlan_table = table.get(port_id)
        print(f"reserve_vlan domain: {domain} vlan_table: {vlan_table}")

        if vlan_table is None:
            print(f"Can't find a mapping for domain:{domain} port:{port_id}")
            return None

        if tag is None:
            # Find the first available one
            for vlan_tag, vlan_available in vlan_table.items():
                if vlan_available:
                    available_tag = vlan_tag
                # TODO: return None if we've scanned the whole table.
        else:
            if vlan_table[tag] is True:
                available_tag = tag
            else:
                available_tag = None

        # available_tag = 200
        return available_tag

    # to be called by delete_connection()
    def unreserve_vlan_breakdown(self, break_down):
        # TODO: implement this
        with self.topology_lock:
            pass

    def unreserve_vlan(self, port):
        # TODO: implement this
        with self.topology_lock:
            pass
