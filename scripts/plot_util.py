import re
import argparse
import json
import os

import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.ticker import PercentFormatter
from distfit import distfit
from fitter import Fitter

from sdx_pce.heuristic.csv_network_parser import *
from sdx_pce.heuristic.network_topology import *

path = "results/"
def plot_util(path, title, tag):
    n_bins=10
    tag_list=tag.split()
    util=[]
    plt_title=[]
    for alg, alg_name in title.items():
        fname=path+tag_list[1]+"_"+alg+"_"+tag_list[2]+"_"+tag_list[3]+"_"+"utility.txt"
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
        axs[i].set_xlabel("Link Utilization")
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
    print(d)
    plt.hist(d, bins=n_bins)
    plt.savefig(path+"demand"+".png")
    plt.clf()  

    f = Fitter(d,
           distributions=['lognorm'])
    f.fit()
    print(f.summary())
    print(f.fitted_param["lognorm"])
    f.plot_pdf()
    f.hist()
    plt.savefig(path+"demand_fit_pdf"+".png")
    plt.clf() 

    dfit = distfit(distr='lognorm')
    results = dfit.fit_transform(np.array(d))
    dfit.plot()
    fig, ax = dfit.plot(chart='pdf')
    plt.savefig(path+"demand_pdf"+".png")


def plot_topology(g):
    filename, file_extension = os.path.splitext(g.name)
    name=filename.split('/')[-1]
    nx.draw(g, with_labels=True)
    plt.savefig(path+name+".png")
    plt.clf()    

def plot_tunnel(g):
    filename, file_extension = os.path.splitext(g.name)
    name=filename.split('/')[-1]
    x=[2,3,4,5]
    #B4
    y_time_te=[0.0032639503479003906,0.00529789924621582,0.006021022796630859,0.0063130855560302734]
    y_time_fcc=[0.11051106452941895,0.12927484512329102,0.15407371520996094,0.1728222370147705]
    y_time_te_cvx=[0.3454568386077881,0.42327284812927246,0.5293939113616943,0.7096188068389893]
    y_time_fcc_cvx=[5.511837959289551,6.940320014953613,7.885976076126099,9.278906106948853]

    plt.plot(x,y_time_te)
    plt.plot(x,y_time_fcc)
    plt.plot(x,y_time_te_cvx)
    #plt.plot(x,y_time_fcc_cvx)
    plt.savefig(path+name+"_tunnel"+".png")
    plt.clf()   

    #uscarrier
    y_time_te=[]
    y_time_fcc=[]
    y_time_te_cvx=[]
    y_time_fcc_cvx=[]

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
            if args.plot=="1": #topology
                plot_topology(network.to_nx_simple()) 
            if args.plot=="2":  #running time
                plot_tunnel(network.to_nx_simple())
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
        tag = "Path B4 1 3"

        plot_util(path, title, tag)