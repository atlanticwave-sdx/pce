import copy
import datetime
import logging
from typing import Mapping

import networkx as nx
from sdx_datamodel.models.topology import (
    TOPOLOGY_INITIAL_VERSION,
    SDX_TOPOLOGY_ID_prefix,
)
from sdx_datamodel.parsing.topologyhandler import TopologyHandler

from .grenmlconverter import GrenmlConverter


class TopologyManager:
    """
    Manager for topology operations.

    Operations are:

        - Merge multiple topologies.

        - Convert to grenml (XML).
    """

    def __init__(self):
        # The merged "super" topology of topologies of different
        # domains, with inter-domain links between them computed.
        self._topology = None

        # Mapping from topology ID to topology.
        self._topology_map = {}

        # Mapping from port ID to link.
        self._port_map = {}

        # Number of interdomain links we computed.
        self._num_interdomain_link = 0

        self._logger = logging.getLogger(__name__)

    def get_handler(self):
        return self.topology_handler

    def topology_id(self, id):
        self._topology._id(id)

    def set_topology(self, topology):
        self._topology = topology

    def get_topology(self):
        return self._topology

    def get_topology_map(self) -> dict:
        return self._topology_map

    def get_port_map(self) -> Mapping[str, dict]:
        """
        Return a mapping between port IDs and links.
        """
        return self._port_map

    def clear_topology(self):
        self._topology = None
        self._topology_map = {}
        self._port_map = {}

    def add_topology(self, data):
        topology = TopologyHandler().import_topology_data(data)
        self._topology_map[topology.id] = topology

        if self._topology is None:
            self._topology = copy.deepcopy(topology)

            # Generate a new topology id
            self.generate_id()

            # Addding to the port list
            links = topology.links
            for link in links:
                for port in link.ports:
                    self._port_map[port["id"]] = link
        else:
            # check the inter-domain links first.
            self._num_interdomain_link += self.inter_domain_check(topology)
            if self._num_interdomain_link == 0:
                self._logger.debug(
                    f"Warning: no interdomain links detected in {topology.id}!"
                )

            # Nodes
            nodes = topology.nodes
            self._topology.add_nodes(nodes)

            # links
            links = topology.links
            self._topology.add_links(links)

            # version
            self.update_version(False)

        self.update_timestamp()

    def get_domain_name(self, node_id):
        """
        Find the topology ID associated with the given node ID.

        A topology ID is expected to be of the format
        "urn:sdx:topology:amlight.net", and from this, we
        can find the domain name associated with the topology.

        TODO: This function name may be a misnomer?
        """
        domain_id = None
        # print(f"len of topology_list: {len(self._topology_map)}")
        for topology_id, topology in self._topology_map.items():
            if topology.has_node_by_id(node_id):
                domain_id = topology_id
                break

        return domain_id

    def generate_id(self):
        self._topology.id = SDX_TOPOLOGY_ID_prefix
        self._topology.version = TOPOLOGY_INITIAL_VERSION
        return id

    def remove_topology(self, topology_id):
        self._topology_map.pop(topology_id, None)
        self.update_version(False)
        self.update_timestamp()

    def is_link_interdomain(self, link, topology):
        """
        Check if a link is an interdomain link.
        """
        for port in link.ports:
            if port['id'] not in self._port_map:
                return True
        return False

    def update_topology(self, data):
        # likely adding new inter-domain links
        update_handler = TopologyHandler()
        topology = update_handler.import_topology_data(data)
        self._topology_map[topology.id] = topology

        # Nodes.
        nodes = topology.nodes
        for node in nodes:
            self._topology.remove_node(node.id)

        # Links.
        links = topology.links
        for link in links:
            if not self.is_link_interdomain(link,topology):
                # print(link.id+";......."+str(link.nni))
                self._topology.remove_link(link.id)
                for port in link.ports:
                    self._port_map.pop(port["id"])

        # Check the inter-domain links first.
        num_interdomain_link = self.inter_domain_check(topology)
        if num_interdomain_link == 0:
            self._logger.warning("Warning: no interdomain links detected!")

        # Nodes.
        nodes = topology.nodes
        self._topology.add_nodes(nodes)

        # Links.
        links = topology.links
        self._topology.add_links(links)

        self.update_version(True)
        self.update_timestamp()

    def update_version(self, sub: bool):
        try:
            [ver, sub_ver] = self._topology.version.split(".")
        except ValueError:
            ver = self._topology.version
            sub_ver = "0"

        self._topology.version = self.new_version(ver, sub_ver, sub)

        return self._topology.version

    def new_version(self, ver, sub_ver, sub: bool):
        if not sub:
            ver = str(int(ver) + 1)
            sub_ver = "0"
        else:
            sub_ver = str(int(sub_ver) + 1)

        return ver + "." + sub_ver

    def update_timestamp(self):
        ct = datetime.datetime.now().isoformat()
        self._topology.timestamp = ct

        return ct

    def inter_domain_check(self, topology):
        interdomain_port_dict = {}
        num_interdomain_link = 0
        links = topology.links
        link_dict = {}
        for link in links:
            link_dict[link.id] = link
            for port in link.ports:
                interdomain_port_dict[port["id"]] = link

        # ToDo: raise an warning or exception
        if len(interdomain_port_dict) == 0:
            self._logger.info("interdomain_port_dict==0")
            return False

        # match any ports in the existing topology
        for port_id in interdomain_port_dict:
            # print("interdomain_port:")
            # print(port_id)
            for existing_port, existing_link in self._port_map.items():
                # print(existing_port)
                if port_id == existing_port:
                    # print("Interdomain port:" + port_id)
                    # remove redundant link between two domains
                    self._topology.remove_link(existing_link.id)
                    num_interdomain_link = +1
            self._port_map[port_id] = interdomain_port_dict[port_id]

        return num_interdomain_link

    # adjacent matrix of the graph, in jason?
    def generate_graph(self):
        graph = nx.Graph()

        if self._topology is None:
            self._logger.warning("We do not have a topology yet")
            return None

        links = self._topology.links
        for link in links:
            inter_domain_link = False
            ports = link.ports
            end_nodes = []
            for port in ports:
                node = self._topology.get_node_by_port(port["id"])
                if node is None:
                    self._logger.warning(
                        f"This port (id: {port['id']}) does not belong to "
                        f"any node in the topology, likely a Non-SDX port!"
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
        self.converter = GrenmlConverter(self._topology)

        return self.converter.read_topology()

    def add_domain_service(self):
        pass

    # may need to read from a configuration file.
    def update_private_properties(self):
        pass

    # on performance properties for now
    def update_link_property(self, link_id, property, value):
        # 1. update the individual topology
        for id, topology in self._topology_map.items():
            links = topology.links
            for link in links:
                self._logger.info(f"link.id={link.id}; id={id}")
                if link.id == link_id:
                    setattr(link, property, value)
                    self._logger.info("updated the link.")
                    # 1.2 need to change the sub_ver of the topology?

        # 2. check on the inter-domain link?
        # 3. update the interodamin topology
        links = self._topology.links
        for link in links:
            if link.id == link_id:
                setattr(link, property, value)
                self._logger.info("updated the link.")
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
        data["timestamp"] = datetime.datetime.now().isoformat()

    def get_port_by_id(self, port_id: str):
        """
        Given port id, returns a Port.
        """
        for node in self.get_topology().nodes:
            for port in node.ports:
                if port.id == port_id:
                    return port.to_dict()
        return None

    def are_two_ports_same_domain(self, port1_id: str, port2_id: str):
        """
        Check if two ports are in the same domain.
        """
        node1 = self.get_topology().get_node_by_port(port1_id)
        node2 = self.get_topology().get_node_by_port(port2_id)
        if node1 is None or node2 is None:
            return False

        domain1 = self.get_domain_name(node1.id)
        domain2 = self.get_domain_name(node2.id)
        return domain1 == domain2

    def update_node_property(self):
        pass

    def update_port_property(self):
        pass
