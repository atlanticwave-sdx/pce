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
from sdx_pce.utils.functions import *

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
    dir="./results_slurm/"
    filename, file_extension = os.path.splitext(g.name)
    name=filename.split('/')[-1]
    #"te", "fcc, "all" figures
    sub="_te"

    n = 11

    time_list_dict = {}
    mean_util_list_dict = {}
    std_util_list_dict = {}
    overprovisioning_list_dict = {}
    unmet_flow_list_dict = {}
    unmet_demands_list_dict = {}
    nc_list_dict = {}

    title = {
        '10': 'TE(CVX)',
        #'11': 'FCC(CVX)',            
        '20': 'TE(GLOP)',
        #'21': 'FCC(GLOP)',
    }

    y_label = [
        "Computation Time (s)",
        "Mean Utility",
        "STD Utility" ,
        "Overprovisioning",
        "Unmet Flows",
        "Unmet Demands",
        "Network Criticality"
    ]

    x_label = "Demand Scale"
    demand_scale_list=[0.5, 1.0, 1.5, 2.0]  

    for a, alg in title.items():
        for g in (0, 1):
            #if a=='10' and g==0:
            #    continue
            key=alg+"_"+str(g)
            time_list = []
            mean_util_list = []
            std_util_list = []
            overprovisioning_list = []
            unmet_flow_list = []
            unmet_demands_list = []
            nc_list = []
            for s in demand_scale_list:
                file=dir+name+"_"+str(a)+"_"+str(s)+"_"+str(g)+"_utility.txt"
                results = last_n_lines(file, n)
                #print(results)
                Optimal=float(results["Optimal"])
                total_flows=float(results["total_flows"])
                overprovisioning = (total_flows-Optimal)/Optimal
                time_list.append(float(results["Time"]))
                mean_util_list.append(float(results["mean_util"]))
                std_util_list.append(float(results["std_util"]))
                overprovisioning_list.append(overprovisioning)
                unmet_flow_list.append(float(results["unmet_flow"]))
                unmet_demands_list.append(float(results["Unmet"]))
                nc_list.append(float(results["NC"]))
            
            time_list_dict[key] = time_list
            mean_util_list_dict[key] = mean_util_list
            std_util_list_dict[key] = std_util_list
            overprovisioning_list_dict[key] = overprovisioning_list
            unmet_flow_list_dict[key] = unmet_flow_list
            unmet_demands_list_dict[key] = unmet_demands_list
            nc_list_dict[key] = nc_list

    fig1, ax1 = plt.subplots()
    ax1.set_title(y_label[0])
    ax1.set_xlabel(x_label)
    plt.yscale("log")  
    for key in time_list_dict.keys():
        ax1.plot(demand_scale_list, time_list_dict[key], label=str(key))

    ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plot_name = y_label[0] + "_" + name + sub + ".png"
    plt.savefig(plot_name, bbox_inches="tight")

    plt.yscale("linear")
    fig2, ax2 = plt.subplots()
    ax2.set_title(y_label[1])
    ax2.set_xlabel(x_label)
    for key in mean_util_list_dict.keys():
        ax2.plot(demand_scale_list, mean_util_list_dict[key], label=str(key))

    ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plot_name = y_label[1] + "_" + name + sub + ".png"
    plt.savefig(plot_name, bbox_inches="tight")

    plt.yscale("linear")
    fig3, ax3 = plt.subplots()
    ax3.set_title(y_label[2])
    ax3.set_xlabel(x_label)
    for key in std_util_list_dict.keys():
        ax3.plot(demand_scale_list, std_util_list_dict[key], label=str(key))

    ax3.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plot_name = y_label[2] + "_" + name + sub + ".png"
    plt.savefig(plot_name, bbox_inches="tight")

    fig4, ax4 = plt.subplots()
    ax4.set_title(y_label[3])
    ax4.set_xlabel(x_label)
    for key in overprovisioning_list_dict.keys():
        ax3.plot(demand_scale_list, overprovisioning_list_dict[key], label=str(key))

    ax4.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plot_name = y_label[3] + "_" + name + sub + ".png"
    plt.savefig(plot_name, bbox_inches="tight")    

    fig5, ax5 = plt.subplots()
    ax5.set_title(y_label[4])
    ax5.set_xlabel(x_label)
    for key in unmet_flow_list_dict.keys():
        ax5.plot(demand_scale_list, unmet_flow_list_dict[key], label=str(key))

    ax5.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plot_name = y_label[4] + "_" + name + sub + ".png"
    plt.savefig(plot_name, bbox_inches="tight") 

    fig6, ax6 = plt.subplots()
    ax6.set_title(y_label[5])
    ax6.set_xlabel(x_label)
    for key in unmet_demands_list_dict.keys():
        ax6.plot(demand_scale_list, unmet_demands_list_dict[key], label=str(key))

    ax6.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plot_name = y_label[5] + "_" + name + sub + ".png"
    plt.savefig(plot_name, bbox_inches="tight") 

    fig7, ax7 = plt.subplots()
    ax7.set_title(y_label[6])
    ax7.set_xlabel(x_label)
    for key in nc_list_dict.keys():
        ax7.plot(demand_scale_list, nc_list_dict[key], label=str(key))

    ax7.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    plot_name = y_label[6] + "_" + name + sub + ".png"
    plt.savefig(plot_name, bbox_inches="tight")     



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