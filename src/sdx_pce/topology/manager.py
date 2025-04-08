import copy
import datetime
import logging
from typing import Mapping

import networkx as nx
from sdx_datamodel.models.link import Link
from sdx_datamodel.models.service import Service
from sdx_datamodel.models.topology import (
    TOPOLOGY_INITIAL_VERSION,
    SDX_TOPOLOGY_ID_prefix,
)
from sdx_datamodel.parsing.topologyhandler import TopologyHandler

from sdx_pce.utils.constants import Constants

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

        # Mapping from port ID to port.
        self._port_map = {}

        # Mapping from port ID to link.
        self._port_link_map = {}

        # Number of interdomain links we computed.
        self._num_interdomain_link = 0

        self._logger = logging.getLogger(__name__)

        # mapping attributes for interdomain links
        self.status_map = {
            ("up", "up"): "up",
            ("up", "error"): "error",
            ("error", "up"): "error",
            ("error", "error"): "error",
            # defaults to down
        }
        self.state_map = {
            ("enabled", "enabled"): "enabled",
            ("maintenance", "maintenance"): "maintenance",
            ("maintenance", "enabled"): "maintenance",
            ("maintenance", "disabled"): "maintenance",
            ("enabled", "maintenance"): "maintenance",
            ("disabled", "maintenance"): "maintenance",
            # defults to disabled
        }
        # bandwidth: the bandwidth attribute will be created based on both port
        # speeds (the minimum of them). Port speed is stored on Port.type and
        # can be 100FE, 1GE, 10GE, 25GE, 40GE, 50GE, 100GE, 400GE, and Other
        # When the value Other is chosen, no bandwidth guaranteed services will
        # be supported, so that we map that value to bandwidth=0
        self.bandwidth_map = {
            "100FE": 0.1,
            "1GE": 1,
            "10GE": 10,
            "25GE": 25,
            "40GE": 40,
            "100GE": 100,
            "400GE": 400,
            "Other": 0,
        }

    def get_handler(self):
        return self.topology_handler

    def topology_id(self, id):
        self._topology._id(id)

    def set_topology(self, topology):
        self._topology = topology

    def get_topology(self):
        return self._topology

    def get_topology_dict(self):
        return self._topology.to_dict()

    def get_topology_map(self) -> dict:
        return self._topology_map

    def get_port_link_map(self) -> Mapping[str, dict]:
        """
        Return a mapping between port IDs and links.
        """
        return self._port_link_map

    def get_port_map(self) -> Mapping[str, dict]:
        """
        Return a mapping between port IDs and ports.
        """
        return self._port_map

    def clear_topology(self):
        self._topology = None
        self._topology_map = {}
        self._port_link_map = {}

    def add_topology(self, data):
        topology = TopologyHandler().import_topology_data(data)
        self._topology_map[topology.id] = topology

        if self._topology is None:
            self._topology = copy.deepcopy(topology)
            interdomain_ports = []

            # Generate a new topology id
            self.generate_id()

            # Addding to the port list
            # links = topology.links
            # for link in links:
            #    for port in link.ports:
            #        self._port_link_map[port["id"]] = link
        else:
            # check the inter-domain links first.
            interdomain_ports = self.inter_domain_check(topology)
            self._num_interdomain_link += len(interdomain_ports)
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
            self.update_version(True)

        # Addding to the port list
        links = topology.links
        for link in links:
            for port in link.ports:
                port_id = port if isinstance(port, str) else port["id"]
                self._port_link_map[port_id] = link

        # Addding to the port node
        nodes = topology.nodes
        for node in nodes:
            for port in node.ports:
                self._port_map[port.id] = port

        # inter-domain links
        self.add_inter_domain_links(topology, interdomain_ports)

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
            port_id = port if isinstance(port, str) else port["id"]
            if port_id not in self._port_link_map:
                return True
        return False

    def is_interdomain_port(self, port_id, topology_id):
        """
        Check if a Port ID is interdomain
        """
        # Sanity checks
        if (
            not isinstance(port_id, str)
            or not port_id.startswith("urn:sdx:port:")
            or not isinstance(topology_id, str)
            or not topology_id.startswith("urn:sdx:topology:")
        ):
            return False
        return port_id.split(":")[3] != topology_id.split(":")[3]

    def get_down_nni_links(self, topology):
        down_nni_links = []
        for node in topology.nodes:
            for port in node.ports:
                if port.nni and port.status == "down":
                    old_port = self.get_port_obj_by_id(self._topology, port.id)
                    if old_port and old_port.status == "up":
                        link = self._port_link_map.get(port.id)
                        if link and link not in down_nni_links:
                            down_nni_links.append(link)
        return down_nni_links

    def get_up_nni_links(self, topology):
        up_nni_links = []
        for node in topology.nodes:
            for port in node.ports:
                if port.nni and port.status == "up":
                    old_port = self.get_port_obj_by_id(self._topology, port.id)
                    if old_port and old_port.status == "down":
                        link = self._port_link_map.get(port.id)
                        if link and link not in up_nni_links:
                            up_nni_links.append(link)
        return up_nni_links

    def get_down_links(self, old_topology, topology):
        """
        Get the links that are down in the new topology.
        """
        down_links = []
        for link in old_topology.links:
            if link.status in ("up", None):
                new_link = topology.get_link_by_id(link.id)
                if new_link and (
                    new_link.status == "down" or new_link.state in ("disabled", None)
                ):
                    down_links.append(link)
                else:  # further check its ports
                    for port_id in link.ports:
                        port = self.get_port_obj_by_id(old_topology, port_id)
                        new_port_id = (
                            next((p for p in new_link.ports if p == port_id), None)
                            if new_link
                            else None
                        )
                        new_port = self.get_port_obj_by_id(topology, new_port_id)
                        if not new_port or (
                            (port.status == "up" and new_port.status == "down")
                            or (
                                port.state == "enabled" and new_port.state == "disabled"
                            )
                        ):
                            new_link = topology.get_link_by_id(link.id)
                            if new_link:
                                new_link = self.update_link_property(
                                    new_link.id, "status", "down"
                                )
                            down_links.append(link)
                            break
        if down_links:
            self._logger.info(
                f"Down links detected: {[link.id for link in down_links]}"
            )
        else:
            self._logger.info("No down links detected.")
        return down_links

    def get_up_links(self, old_topology, topology):
        """
        Get the links that are down in the new topology.
        """
        up_links = []
        for link in old_topology.links:
            if link.status in ("down", None) or link.state in ("disabled", None):
                new_link = topology.get_link_by_id(link.id)
                if new_link is not None and (
                    new_link.status == "up" and new_link.state in ("enabled", None)
                ):
                    up_links.append(new_link)
        return up_links

    def topology_diff(self, old_topology, topology):

        added_nodes = set()
        added_links = set()
        removed_nodes = set()
        removed_links = set()

        # obtain the objects
        removed_links_list = []
        added_links_list = []
        removed_nodes_list = []
        added_nodes_list = []

        if old_topology is not None:
            removed_nodes = set(old_topology.nodes_id()).difference(
                set(topology.nodes_id())
            )
            added_nodes = set(topology.nodes_id()).difference(
                set(old_topology.nodes_id())
            )
            removed_links = set(old_topology.links_id()).difference(
                set(topology.links_id())
            )
            added_links = set(topology.links_id()).difference(
                set(old_topology.links_id())
            )
        else:
            self._logger.warning(
                f"No existing topology found for update: {topology.id}"
            )
            self._logger.info(f"Topology map keys: {list(self._topology_map.keys())}")
            return (
                removed_nodes_list,
                added_nodes_list,
                removed_links_list,
                added_links_list,
            )

        for link_id in removed_links:
            link_obj = old_topology.get_link_by_id(link_id)
            if link_obj is not None:
                removed_links_list.append(link_obj)
        for link_id in added_links:
            link_obj = topology.get_link_by_id(link_id)
            if link_obj is not None:
                added_links_list.append(link_obj)
        for node_id in removed_nodes:
            node_obj = old_topology.get_node_by_id(node_id)
            if node_obj is not None:
                removed_nodes_list.append(node_obj)
        for node_id in added_nodes:
            node_obj = topology.get_node_by_id(node_id)
            if node_obj is not None:
                added_nodes_list.append(node_obj)

        # adding the down links to the removed links list
        down_links = self.get_down_links(old_topology, topology)

        for link in down_links:
            if link not in removed_links_list:
                removed_links_list.append(link)

        # adding the up links to the added links list
        up_links = self.get_up_links(old_topology, topology)

        for link in up_links:
            added_links_list.append(link)

        return (
            removed_nodes_list,
            added_nodes_list,
            removed_links_list,
            added_links_list,
        )

    def update_topology(self, data):
        # likely adding new inter-domain links
        update_handler = TopologyHandler()
        topology = update_handler.import_topology_data(data)
        old_topology = self._topology_map.get(topology.id)
        self._topology_map[topology.id] = topology

        # Nodes.
        nodes = topology.nodes
        for node in nodes:
            self._topology.remove_node(node.id)

        # Links.
        links = topology.links
        for link in links:
            if not self.is_link_interdomain(link, topology):
                # print(link.id+";......."+str(link.nni))
                self._topology.remove_link(link.id)
                for port in link.ports:
                    port_id = port if isinstance(port, str) else port["id"]
                    self._port_link_map.pop(port_id)

        # Check the inter-domain links first.
        interdomain_ports = self.inter_domain_check(topology)
        if len(interdomain_ports) == 0:
            self._logger.warning("Warning: no interdomain links detected!")

        # Nodes.
        nodes = topology.nodes
        self._topology.add_nodes(nodes)

        # Links.
        links = topology.links
        self._topology.add_links(links)

        # inter-domain links
        self.add_inter_domain_links(topology, interdomain_ports)

        # Update the port node map
        for node in topology.nodes:
            for port in node.ports:
                self._port_map[port.id] = port

        # Addding to the port list
        links = topology.links
        for link in links:
            for port in link.ports:
                port_id = port if isinstance(port, str) else port["id"]
                self._port_link_map[port_id] = link

        # extract the changes for controller rerouting actions: link removal and link down
        (removed_nodes_list, added_nodes_list, removed_links_list, added_links_list) = (
            self.topology_diff(old_topology, topology)
        )

        if topology.version > old_topology.version:
            self.update_version(True)
        if topology.timestamp != old_topology.timestamp:
            self.update_timestamp()

        # extra link status changes: up <-> down that is associated with nni port status changes: up <-> down
        # comparing with the global topology to catch nni links

        get_down_nni_links = self.get_down_nni_links(topology)
        for link in get_down_nni_links:
            if link not in removed_links_list:
                removed_links_list.append(link)

        get_up_nni_links = self.get_up_nni_links(topology)
        for link in get_up_nni_links:
            if link not in added_links_list:
                added_links_list.append(link)

        return (
            removed_nodes_list,
            added_nodes_list,
            removed_links_list,
            added_links_list,
        )

    def update_version(self, sub: bool):
        try:
            [ver, sub_ver] = self._topology.version.split(".")
        except ValueError:
            ver = self._topology.version
            sub_ver = "0"

        self._topology.version = self.new_version(ver, sub_ver, sub)

        return self._topology.version

    def new_version(self, ver, sub_ver, sub: bool):
        new_version = ver
        if sub:
            new_version = str(int(ver) + 1)

        if sub_ver != "0":
            new_version = ver + "." + str(int(sub_ver) + 1)

        return new_version

    def update_timestamp(self):
        ct = datetime.datetime.now().isoformat()
        self._topology.timestamp = ct

        return ct

    def inter_domain_check(self, topology):
        interdomain_port_dict = {}
        interdomain_ports = []
        interdomain_port_ids = []
        links = topology.links
        link_dict = {}
        for link in links:
            link_dict[link.id] = link
            for port in link.ports:
                port_id = port if isinstance(port, str) else port["id"]
                interdomain_port_dict[port_id] = link

        # match any ports in the existing topology
        for port_id in interdomain_port_dict:
            # print("interdomain_port:")
            # print(port_id)
            for existing_port, existing_link in self._port_link_map.items():
                # print(existing_port)
                if port_id == existing_port:
                    # print("Interdomain port:" + port_id)
                    # remove redundant link between two domains
                    self._topology.remove_link(existing_link.id)
                    interdomain_port_ids.append(port_id)
            self._port_link_map[port_id] = interdomain_port_dict[port_id]

        # count for inter-domain links according to topo spec 2.0.x
        for node in topology.nodes:
            for port in node.ports:
                # interdomain ports based on previous methodology
                if port.id in interdomain_port_ids:
                    interdomain_ports.append(port)
                # interdomain ports based on new methodology (spec 2.0)
                if self.is_interdomain_port(port.nni, topology.id):
                    interdomain_ports.append(port)

        return interdomain_ports

    def create_update_interdomain_link(self, port1, port2):
        """Create or update an interdomain link from two ports."""
        if port2.id < port1.id:
            port1, port2 = port2, port1

        port1_id = port1.id.replace("urn:sdx:port:", "", 1)
        port2_id = port2.id.replace("urn:sdx:port:", "", 1)
        link_id = f"urn:sdx:link:interdomain:{port1_id}:{port2_id}"

        for link in self._topology.links:
            if link_id == link.id:
                break
        else:
            link = Link(
                id=link_id,
                name=f"{port1.name}--{port2.name}",
                ports=[port1.id, port2.id],
                bandwidth=min(
                    self.bandwidth_map.get(port1.type, 100),
                    self.bandwidth_map.get(port2.type, 100),
                ),
                residual_bandwidth=100,
                latency=0,
                packet_loss=0,
                availability=100,
            )
            self._topology.add_links([link])

        link.status = self.status_map.get((port1.status, port2.status), "down")
        link.state = self.state_map.get((port1.state, port2.state), "disabled")

    def add_inter_domain_links(self, topology, interdomain_ports):
        """Add inter-domain links (whenever possible)."""
        for port in interdomain_ports:
            other_port = self._port_map.get(port.nni)
            if not other_port or other_port.nni != port.id:
                self._logger.warning(
                    "Interdomain link not added now - didnt find other port:"
                    f" port={port.id} other_port={port.nni} ({other_port})"
                )
                continue
            self.create_update_interdomain_link(port, other_port)

    def get_failed_links(self) -> dict:
        """Get failed links on the topology (ie., Links not up and enabled)."""
        failed_links = []
        for link in self._topology.links:
            if link.status in ("up", None) and link.state in ("enabled", None):
                continue
            failed_links.append({"id": link.id, "ports": link.ports})
        return failed_links

    # adjacent matrix of the graph, in jason?
    def generate_graph(self):
        graph = nx.Graph()

        if self._topology is None:
            self._logger.warning("We do not have a topology yet")
            return None

        links = self._topology.links
        for link in links:
            inter_domain_link = False
            if link.status not in ("up", None) or link.state not in ("enabled", None):
                continue
            ports = link.ports
            end_nodes = []
            for port in ports:
                port_id = port if isinstance(port, str) else port["id"]
                node = self._topology.get_node_by_port(port_id)
                if node is None:
                    self._logger.warning(
                        f"This port (id: {port_id}) does not belong to "
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
                edge[Constants.LATENCY] = link.latency
                edge[Constants.BANDWIDTH] = (
                    link.bandwidth * link.residual_bandwidth * 0.01
                )
                edge[Constants.RESIDUAL_BANDWIDTH] = (
                    link.residual_bandwidth
                )  # this is a percentage
                edge["weight"] = 1000.0 * (1.0 / link.residual_bandwidth)
                edge[Constants.PACKET_LOSS] = link.packet_loss
                edge[Constants.AVAILABILITY] = link.availability

        return graph

    def generate_grenml(self):
        self.converter = GrenmlConverter(self._topology)

        return self.converter.read_topology()

    def add_domain_service(self):
        pass

    # may need to read from a configuration file.
    def update_private_properties(self):
        pass

    def get_residul_bandwidth(self) -> dict:
        """
        Get the residual bandwidth on each link in the topology.

        :return: A dictionary indexed by the link ID with residual bandwidth as values.
        """
        residual_bandwidth = {}
        links = self._topology.links

        for link in links:
            link_id = link.id
            residual_bw = link.__getattribute__(Constants.RESIDUAL_BANDWIDTH)
            if residual_bw is not None:
                residual_bandwidth[link_id] = residual_bw
            else:
                self._logger.warning(f"Residual bandwidth not found for link {link_id}")

        return residual_bandwidth

    # on performance properties for now
    def update_link_property(self, link_id, property, value):
        # 1. update the individual topology
        for id, topology in self._topology_map.items():
            link = topology.get_link_by_id(link_id)
            if link is not None:
                setattr(link, property, value)
                self._logger.info("updated the link.")
                # 1.2 need to change the sub_ver of the topology?

        # 2. check on the inter-domain link?
        # update the interdomain topology
        link = self._topology.get_link_by_id(link_id)

        if link is not None:
            setattr(link, property, value)
            self._logger.info(f"updated the link:{link_id} {property} to {value}")

        return link

    # on performance properties for now
    def change_link_property_by_value(
        self, port_id_0, port_id_1, property, value, replace=True
    ):
        # If it's bandwdith, we need to update the residual bandwidth as a percentage
        # "bandwidth" remains to keep the original port bandwidth in topology json.
        # in the graph model, linkd bandwidth is computed as bandwidth*residual_bandwidth*0.01
        # 1. update the individual topology
        for id, topology in self._topology_map.items():
            link = topology.get_link_by_port_id(port_id_0, port_id_1)
            if link is not None:
                orignial_bw = link.__getattribute__(Constants.BANDWIDTH)
                residual = link.__getattribute__(property)
                if property == Constants.RESIDUAL_BANDWIDTH:
                    if replace is False:
                        residual_bw = (
                            link.__getattribute__(Constants.BANDWIDTH) * residual * 0.01
                        )
                        self._logger.info(
                            "updated the link:"
                            + str(residual_bw)
                            + " value:"
                            + str(value)
                        )
                        new_residual = max(
                            (residual_bw + value) * 100 / orignial_bw, 0.001
                        )
                    else:
                        new_residual = value
                    setattr(link, property, new_residual)
                    self._logger.info(
                        "updated the link:"
                        + link._id
                        + ":"
                        + property
                        + " from "
                        + str(residual)
                        + " to "
                        + str(new_residual)
                    )
                # 1.2 need to change the sub_ver of the topology?

        # 2. check on the inter-domain link?
        # update the interdomain topology
        link = self._topology.get_link_by_port_id(port_id_0, port_id_1)
        if link is not None:
            orignial_bw = link.__getattribute__(Constants.BANDWIDTH)
            residual = link.__getattribute__(property)
            if property == Constants.RESIDUAL_BANDWIDTH:
                if replace is False:
                    residual_bw = (
                        link.__getattribute__(Constants.BANDWIDTH) * residual * 0.01
                    )
                    new_residual = max((residual_bw + value) * 100 / orignial_bw, 0.001)
                else:
                    new_residual = value
                setattr(link, property, new_residual)
                self._logger.info(
                    "updated the link:"
                    + link._id
                    + ":"
                    + property
                    + " from "
                    + str(residual)
                    + " to "
                    + str(new_residual)
                )
            # 2.2 need to change the sub_ver of the topology?

    def change_port_vlan_range(self, topology_id, port_id, value):
        topology = self._topology_map.get(topology_id)
        port = self.get_port_obj_by_id(topology, port_id)
        if port is None:
            self._logger.debug(f"Port not found in changing vlan range:{port_id}")
            return None
        self._logger.debug(f"Port found:{port_id};new vlan range:{value}")

        vlan_range_v1 = port.__getattribute__("vlan_range")
        if vlan_range_v1:
            port.__setattr__("vlan_range", value)
        services = port.__getattribute__(Constants.SERVICES)
        if services:
            l2vpn_ptp = services.__getattribute__(Constants.L2VPN_P2P)
            if l2vpn_ptp:
                l2vpn_ptp["vlan_range"] = value
        else:
            self._logger.debug(f"Port has no services (v2):{port_id}")
            l2vpn_ptp = {}
            l2vpn_ptmp = {}
            l2vpn_ptp["vlan_range"] = value
            services = Service(l2vpn_ptp=l2vpn_ptp, l2vpn_ptmp=l2vpn_ptmp)
            port.__setattr__(Constants.SERVICES, services)

        # update the whole topology
        topology = self.get_topology()
        port = self.get_port_obj_by_id(topology, port_id)
        if port is None:
            self._logger.debug(f"Port not found in changing vlan range:{port_id}")
            return None
        self._logger.debug(f"Port found:{port_id};new vlan range:{value}")
        vlan_range_v1 = port.__getattribute__("vlan_range")
        if vlan_range_v1:
            port.__setattr__("vlan_range", value)
        port.__setattr__(Constants.SERVICES, services)

        self._logger.info(
            "updated the port:" + port_id + " vlan_range" + " to " + str(value)
        )

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

    def get_port_obj_by_id(self, topology, port_id: str):
        """
        Given port id, returns a Port.
        """
        for node in topology.nodes:
            for port in node.ports:
                if port.id == port_id:
                    return port
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
