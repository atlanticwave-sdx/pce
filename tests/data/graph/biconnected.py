import sys

from Utility import functions

link_list = {
    "1": ["4", "2"],
    "2": ["1", "3"],
    "3": ["4", "2", "5", "6"],
    "4": ["1", "3"],
    "5": ["3", "6"],
    "6": ["3", "5"],
}
node_list = functions.create_unvisited_list(link_list)
print(node_list)
