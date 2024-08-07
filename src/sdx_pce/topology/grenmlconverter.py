import logging

from grenml import GRENMLManager
from grenml.models.nodes import Node
from sdx_datamodel.models.topology import Topology

from sdx_pce.utils.constants import Constants


class GrenmlConverter(object):
    def __init__(self, topology: Topology):
        self.topology = topology
        self.grenml_manager = GRENMLManager(topology.name)

    def set_topology(self, topology: Topology):
        self.topology = topology

    def read_topology(self):
        domain_service = self.topology.services
        if domain_service is not None:
            owner = domain_service.owner
        else:
            owner = Constants.DEFAULT_OWNER
        self.grenml_manager.set_primary_owner(owner)
        self.grenml_manager.add_institution(owner, owner)

        self.add_nodes(self.topology.nodes)

        self.add_links(self.topology.links)

        self.topology_str = self.grenml_manager.write_to_string()

    def add_nodes(self, nodes):
        for node in nodes:
            location = node.location
            logging.info(f"adding node: {node.id}")
            self.grenml_manager.add_node(
                node.id,
                node.name,
                node.short_name,
                longitude=location.longitude,
                latitude=location.latitude,
                iso3166_2_lvl4=location.iso3166_2_lvl4,
                address=location.address,
            )

    def add_links(self, links):
        for link in links:
            inter_domain_link = False
            ports = link.ports
            end_nodes = []
            for port in ports:
                node = self.topology.get_node_by_port(port["id"])
                if node is not None:
                    location = node.location
                    grenml_node = Node(
                        node.id,
                        node.name,
                        node.short_name,
                        longitude=location.longitude,
                        latitude=location.latitude,
                        iso3166_2_lvl4=location.iso3166_2_lvl4,
                        address=location.address,
                    )
                    end_nodes.append(grenml_node)
                else:
                    logging.warning(
                        f"This port ({port['id']}) doesn't belong to any "
                        f"node in the topology, likely an Interdomain port?"
                    )
                    inter_domain_link = True
            if not inter_domain_link:
                self.grenml_manager.add_link(
                    link.id, link.name, link.short_name, nodes=end_nodes
                )

    def get_xml_str(self):
        return self.topology_str
