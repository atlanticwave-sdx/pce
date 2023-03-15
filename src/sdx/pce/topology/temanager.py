import networkx as nx
from networkx.algorithms import approximation as approx

from sdx.datamodel.parsing.connectionhandler import ConnectionHandler
from sdx.pce.models import (
    ConnectionPath,
    ConnectionRequest,
    ConnectionSolution,
    TrafficMatrix,
)
from sdx.pce.topology.manager import TopologyManager


class TEManager:

    """
    TE Manager for connection - topology operations.

    Functions of this class are:

        - generate inputs to the PCE solver

        - converter the solver output.
    """

    def __init__(self, topology_data, connection_data):
        super().__init__()

        self.topology_manager = TopologyManager()
        self.connection_handler = ConnectionHandler()

        self.topology_manager.topology = (
            self.topology_manager.get_handler().import_topology_data(topology_data)
        )
        self.connection = self.connection_handler.import_connection_data(
            connection_data
        )

        self.graph = self.generate_graph_te()

    def add_topology(self, topology_data: dict):
        """
        Add a new topology to TEManager.

        :param topology_data: a dictionary that represents a topology.
        """
        self.topology_manager.add_topology(topology_data)

    def generate_connection_te(self) -> TrafficMatrix:
        """
        Generate a Traffic Matrix from the connection request we have.
        """
        ingress_port = self.connection.ingress_port
        ingress_node = self.topology_manager.topology.get_node_by_port(ingress_port.id)
        egress_port = self.connection.egress_port
        egress_node = self.topology_manager.topology.get_node_by_port(egress_port.id)

        ingress_nodes = [
            x for x, y in self.graph.nodes(data=True) if y["id"] == ingress_node.id
        ]

        egress_nodes = [
            x for x, y in self.graph.nodes(data=True) if y["id"] == egress_node.id
        ]

        if len(ingress_nodes) <= 0:
            raise Exception("No ingress nodes found in the graph")

        if len(egress_nodes) <= 0:
            raise Exception("No egress nodes found in the graph")

        required_bandwidth = self.connection.bandwidth
        required_latency = self.connection.latency

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

    def generate_connection_breakdown_tm(self, connection: ConnectionSolution):
        """
        Take a connection and generate a breakdown.

        TODO: This is work in progress, and this is an alternative to
        generate_connection_breakdown() below.
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

    def generate_connection_breakdown(self, connection):
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
