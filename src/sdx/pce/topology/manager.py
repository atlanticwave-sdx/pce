import copy
import datetime

import networkx as nx

from sdx.datamodel.models.topology import (
    TOPOLOGY_INITIAL_VERSION,
    SDX_TOPOLOGY_ID_prefix,
)
from sdx.datamodel.parsing.topologyhandler import TopologyHandler

from .grenmlconverter import GrenmlConverter


class TopologyManager:

    """
    Manager for topology operations.

    Operations are:

        - Merge multiple topologies.

        - Convert to grenml (XML).
    """

    def __init__(self):
        super().__init__()

        self.handler = TopologyHandler()

        self.topology = None
        self.topology_list = {}
        self.port_list = {}  # {port, link}

        self.num_interdomain_link = 0

    def get_handler(self):
        return self.handler

    def topology_id(self, id):
        self.topology._id(id)

    def set_topology(self, topology):
        self.topology = topology

    def get_topology(self):
        return self.topology

    def clear_topology(self):
        self.topology = None
        self.topology_list = {}
        self.port_list = {}

    def add_topology(self, data):
        topology = self.handler.import_topology_data(data)
        self.topology_list[topology.id] = topology

        if self.topology is None:
            self.topology = copy.deepcopy(topology)

            # Generate a new topology id
            self.generate_id()

            # Addding to the port list
            links = topology.get_links()
            for link in links:
                for port in link.ports:
                    self.port_list[port["id"]] = link
        else:
            # check the inter-domain links first.
            self.num_interdomain_link += self.inter_domain_check(topology)
            if self.num_interdomain_link == 0:
                print("Warning: no interdomain links detected!")

            # Nodes
            nodes = topology.get_nodes()
            self.topology.add_nodes(nodes)

            # links
            links = topology.get_links()
            self.topology.add_links(links)

            # version
            self.update_version(False)

        self.update_timestamp()

    def get_domain_name(self, node_id):
        domain_id = None
        # print("len of topology_list:"+str(len(self.topology_list)))
        for id, topology in self.topology_list.items():
            if topology.has_node_by_id(node_id):
                domain_id = id
                break
        return domain_id

    def generate_id(self):
        self.topology.set_id(SDX_TOPOLOGY_ID_prefix)
        self.topology.version = TOPOLOGY_INITIAL_VERSION
        return id

    def remove_topology(self, topology_id):
        self.topology_list.pop(topology_id, None)
        self.update_version(False)
        self.update_timestamp()

    def update_topology(self, data):
        # likely adding new inter-domain links
        update_handler = TopologyHandler()
        topology = update_handler.import_topology_data(data)
        self.topology_list[topology.id] = topology

        # Nodes.
        nodes = topology.get_nodes()
        for node in nodes:
            self.topology.remove_node(node.id)

        # Links.
        links = topology.get_links()
        for link in links:
            if not link.nni:
                # print(link.id+";......."+str(link.nni))
                self.topology.remove_link(link.id)
                for port in link.ports:
                    self.port_list.pop(port["id"])

        # Check the inter-domain links first.
        num_interdomain_link = self.inter_domain_check(topology)
        if num_interdomain_link == 0:
            print("Warning: no interdomain links detected!")

        # Nodes.
        nodes = topology.get_nodes()
        self.topology.add_nodes(nodes)

        # Links.
        links = topology.get_links()
        self.topology.add_links(links)

        self.update_version(True)
        self.update_timestamp()

    def update_version(self, sub: bool):
        try:
            [ver, sub_ver] = self.topology.version.split(".")
        except ValueError:
            ver = self.topology.version
            sub_ver = "0"

        self.topology.version = self.new_version(ver, sub_ver, sub)

        return self.topology.version

    def new_version(self, ver, sub_ver, sub: bool):
        if not sub:
            ver = str(int(ver) + 1)
            sub_ver = "0"
        else:
            sub_ver = str(int(sub_ver) + 1)

        return ver + "." + sub_ver

    def update_timestamp(self):
        ct = datetime.datetime.now().isoformat()
        self.topology.time_stamp = ct

        return ct

    def inter_domain_check(self, topology):
        interdomain_port_dict = {}
        num_interdomain_link = 0
        links = topology.get_links()
        link_dict = {}
        for link in links:
            link_dict[link.id] = link
            for port in link.ports:
                interdomain_port_dict[port["id"]] = link

        # ToDo: raise an warning or exception
        if len(interdomain_port_dict) == 0:
            print("interdomain_port_dict==0")
            return False

        # match any ports in the existing topology
        for port_id in interdomain_port_dict:
            # print("interdomain_port:")
            # print(port_id)
            for existing_port, existing_link in self.port_list.items():
                # print(existing_port)
                if port_id == existing_port:
                    # print("Interdomain port:" + port_id)
                    # remove redundant link between two domains
                    self.topology.remove_link(existing_link.id)
                    num_interdomain_link = +1
            self.port_list[port_id] = interdomain_port_dict[port_id]

        return num_interdomain_link

    # adjacent matrix of the graph, in jason?
    def generate_graph(self):
        graph = nx.Graph()
        links = self.topology.links
        for link in links:
            inter_domain_link = False
            ports = link.ports
            end_nodes = []
            for port in ports:
                node = self.topology.get_node_by_port(port["id"])
                if node is None:
                    print(
                        "This port doesn't belong to any node in the topology, likely a Non-SDX port!"
                        + port["id"]
                    )
                    inter_domain_link = True
                    break
                else:
                    end_nodes.append(node)
                    # print("graph node:"+node.id)
            if not inter_domain_link:
                graph.add_edge(end_nodes[0].id, end_nodes[1].id)
                edge = graph.edges[end_nodes[0].id, end_nodes[1].id]
                edge["id"] = link.id
                edge["latency"] = link.latency
                edge["bandwidth"] = link.bandwidth
                edge["residual_bandwidth"] = link.residual_bandwidth
                edge["weight"] = 1000.0 * (1.0 / link.residual_bandwidth)
                edge["packet_loss"] = link.packet_loss
                edge["availability"] = link.availability

        return graph

    def generate_grenml(self):
        self.converter = GrenmlConverter(self.topology)

        return self.converter.read_topology()

    def add_domain_service(self):
        pass

    # may need to read from a configuration file.
    def update_private_properties(self):
        pass

    # on performance properties for now
    def update_link_property(self, link_id, property, value):
        # 1. update the individual topology
        for id, topology in self.topology_list.items():
            links = topology.get_links()
            for link in links:
                print(link.id + ";" + id)
                if link.id == link_id:
                    setattr(link, property, value)
                    print("updated the link.")
                    # 1.2 need to change the sub_ver of the topology?

        # 2. check on the inter-domain link?
        # 3. update the interodamin topology
        links = self.topology.get_links()
        for link in links:
            if link.id == link_id:
                setattr(link, property, value)
                print("updated the link.")
                # 2.2 need to change the sub_ver of the topology?

        self.update_version(True)
        self.update_timestamp()
        # 4. Signal update the (networkx) graph

        # 5. signal Reoptimization of TE?

    def update_element_property_json(self, data, element, element_id, property, value):
        elements = data[element]
        for element in elements:
            if element["id"] == element_id:
                element[property] = value

        try:
            [ver, sub_ver] = data["version"].split(".")
        except ValueError:
            ver = "0"
            sub_ver = "0"

        data["version"] = self.new_version(ver, sub_ver, True)
        data["time_stamp"] = datetime.datetime.now().isoformat()

    def update_node_property(self):
        pass

    def update_port_property(self):
        pass
