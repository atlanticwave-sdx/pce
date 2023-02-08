import networkx as nx
from networkx.algorithms import approximation as approx

from sdx.datamodel.parsing.connectionhandler import ConnectionHandler
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

        self.manager = TopologyManager()
        self.connection_handler = ConnectionHandler()

        self.manager.topology = self.manager.get_handler().import_topology_data(
            topology_data
        )
        self.connection = self.connection_handler.import_connection_data(
            connection_data
        )

        self.graph = self.generate_graph_te()

    def generate_connection_te(self):
        ingress_port = self.connection.ingress_port
        ingress_node = self.manager.topology.get_node_by_port(ingress_port.id)
        egress_port = self.connection.egress_port
        egress_node = self.manager.topology.get_node_by_port(egress_port.id)

        i_node = [
            x for x, y in self.graph.nodes(data=True) if y["id"] == ingress_node.id
        ]
        e_node = [
            x for x, y in self.graph.nodes(data=True) if y["id"] == egress_node.id
        ]

        bandwidth_required = self.connection.bandwidth
        latency_required = self.connection.latency

        requests = []
        request = [i_node[0], e_node[0], bandwidth_required, latency_required]
        requests.append(request)

        return requests

    def generate_graph_te(self):
        graph = self.manager.generate_graph()
        graph = nx.convert_node_labels_to_integers(graph, label_attribute="id")
        self.graph = graph
        # print(list(graph.nodes(data=True)))
        return graph

    def graph_node_connectivity(self, source=None, dest=None):
        conn = approx.node_connectivity(self.graph, source, dest)
        return conn

    def requests_connectivity(self, requests):
        for request in requests:
            conn = self.graph_node_connectivity(request[0], request[1])
            print(
                "Request Connectivity: {}, {} = {}".format(
                    request[0],
                    request[1],
                    conn,
                )
            )
        return True

    def generate_connection_breakdown(self, connection):
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

                domain_1 = self.manager.get_domain_name(node_1["id"])
                domain_2 = self.manager.get_domain_name(node_2["id"])

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
                n1, p1, n2, p2 = self.manager.topology.get_port_by_link(n1, n2)
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
                n1, p1, n2, p2 = self.manager.topology.get_port_by_link(n1, n2)
                i_port = next_i
                e_port = p1
                next_i = p2
            segment["ingress_port"] = i_port
            segment["egress_port"] = e_port
            domain_breakdown[domain] = segment.copy()
            i = i + 1

        print(f"generate_connection_breakdown(): domain_breakdown: {domain_breakdown}")
        return domain_breakdown
