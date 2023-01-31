from grenml import GRENMLManager
from grenml.models.nodes import Node
from grenml.models.links import Link

from sdx.datamodel.models.topology import Topology

# from models.node import Node
# from sdx.datamodel.models.location import Location


class GrenmlConverter(object):
    def __init__(self, topology: Topology):
        self.topology = topology
        self.grenml_manager = GRENMLManager(topology.name)

    def set_topology(self, topology: Topology):
        self.topology = topology

    def read_topology(self):
        domain_service = self.topology.get_domain_service()
        owner = domain_service.owner
        self.grenml_manager.set_primary_owner(owner)

        self.grenml_manager.add_institution(owner, owner)

        self.add_nodes(self.topology.get_nodes())

        self.add_links(self.topology.get_links())

        self.topology_str = self.grenml_manager.write_to_string()

        # print(self.topology_str)

    def add_nodes(self, nodes):
        for node in nodes:
            location = node.get_location()
            print("adding node:" + node.id)
            self.grenml_manager.add_node(
                node.id,
                node.name,
                node.short_name,
                longitude=location.longitude,
                latitude=location.latitude,
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
                    location = node.get_location()
                    grenml_node = Node(
                        node.id,
                        node.name,
                        node.short_name,
                        longitude=location.longitude,
                        latitude=location.latitude,
                        address=location.address,
                    )
                    end_nodes.append(grenml_node)
                else:
                    print(
                        "This port doesn't belong to any node in the topology, likely an Interdomain port!"
                        + port["id"]
                    )
                    inter_domain_link = True
            if not inter_domain_link:
                self.grenml_manager.add_link(
                    link.id, link.name, link.short_name, nodes=end_nodes
                )

    def get_xml_str(self):
        return self.topology_str
