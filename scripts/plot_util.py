import re
import argparse
import json
import os

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import PercentFormatter

from sdx_pce.heuristic.csv_network_parser import *
from sdx_pce.heuristic.network_topology import *

path = "results/"
def plot_util(path, title, tag):
    n_bins=10
    tag_list=tag.split()
    util=[]
    plt_title=[]
    for alg, alg_name in title.items():
        fname=path+tag_list[1]+"_"+alg+"_"+tag_list[2]+"_"+"utility.txt"
        plt_title.append(alg_name)
        with open(fname) as file:
            # loop to read iterate
            results = {}
            for line in file.readlines():
                # print(line, end ='')
                result=line.split(":")
                results[result[0]]=float(result[1].strip())
        util.append(results)

    # We can set the number of bins with the *bins* keyword argument.
    #edge=list(util[0].keys())
    #print(f"{type(edge)}:{edge}")
    #print(util[0].values())
    #plt.xticks(range(len(edge)), edge, size='small')
    num_plot=len(title)
    fig, axs = plt.subplots(1, num_plot, sharey=True, tight_layout=True)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    for i in range(num_plot):
        axs[i].set_title(plt_title[i])
        axs[i].set_xlabel("Link Utility")
        axs[i].hist(list(util[i].values()), weights=np.ones(len(util[i].values())) / len(util[i].values()), bins=n_bins,density=True, histtype="step",
                               cumulative=True)
        axs[i].hist(list(util[i].values()), weights=np.ones(len(util[i].values())) / len(util[i].values()), bins=n_bins)

    name = "_".join(tag_list) + ".png"
    plt.savefig(path+name, bbox_inches="tight")

def plot_unmet():
    pass

def plot_demands(network):
    n_bins=10
    print("Plot Demands Distribution!\n")
    demands=network.demands
    d=[x.amount for x in demands.values()]
    print(len(d))
    plt.hist(d, bins=n_bins)
    plt.savefig(path+"demand"+".png")
    plt.clf()  

def plot_topology(g):
    filename, file_extension = os.path.splitext(g.name)
    name=filename.split('/')[-1]
    nx.draw(g, with_labels=True)
    plt.savefig(path+name+".png")
    plt.clf()    

if __name__ == "__main__":
    parse = argparse.ArgumentParser()
    parse.add_argument(
        "-t",
        dest="te_file",
        required=False,
        help="Input file for the connections or traiffc matrix, e.g. c connection.json. Required.",
        type=str,
    )
    parse.add_argument(
        "-n",
        dest="topology_file",
        required=False,
        help="Input file for the network topology, e.g. t topology.json. Required.",
        type=str,
    )
    parse.add_argument(
        "-p",
        dest="plot",
        required=False,
        help="plot choice, saved under ./results/",
        type=str,
    )

    parse.print_help()
    args = parse.parse_args()
    #plot topology and demands
    if args.topology_file is not None:
        filename, file_extension = os.path.splitext(args.topology_file)
        network=None
        if (file_extension=='.txt') or (file_extension=='.csv'):
            print(f"ext:{file_extension}")
            network = parse_topology(args.topology_file)
        if file_extension=='.json':
            network = parse_topology_json(args.topology_file) 
        if args.plot is not None:
            if args.plot=="1":
                plot_topology(network.to_nx_simple())       
        if args.te_file is not None:    
            demands=parse_demands(network, args.te_file)
            if args.plot is not None:
                if args.plot=="1":
                    plot_demands(network)   
    else:
        #plot results

        title = {
            '20': 'TE',
            '21': 'FCC',
            #'22': 'CAT',
        }
        tag = "Path B4 1 "

        plot_util(path, title, tag)