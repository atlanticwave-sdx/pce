import json

import matplotlib.pyplot as plt
import numpy as np

from sdx.pce.LoadBalancing.MC_Solver import runMC_Solver
from sdx.pce.LoadBalancing.RandomTopologyGenerator import lbnxgraphgenerator


def filesave(file):
    with open("../test/data/graphdata2.json", "w") as json_file:
        json.dump(file, json_file, indent=4)


def draw_errorbar(nodes, avglist, std, name):
    labels = []
    x_axis = []
    for num in range(nodes[0], nodes[1]):
        labels.append(str(num))
        x_axis.append(num)

    x_pos = np.arange(len(labels))
    fig, ax = plt.subplots()
    ax.bar(
        x_pos, avglist, yerr=std, align="center", alpha=0.5, ecolor="black", capsize=10
    )

    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels)
    ax.set_title(name)
    ax.yaxis.grid(True)
    ax.set_xlabel("Number of Nodes")
    ax.set_ylabel("Path Weights")

    plt.tight_layout()
    plt.savefig("Heuristic Std Error.png", dpi=300)
    plt.show()


def draw_comparisiontime(
    nodes, solvertimelist, heurtimelist_latency, heurtimelist_weight
):
    labels = []
    x_axis = []
    for num in range(nodes[0], nodes[1]):
        labels.append(str(num))
        x_axis.append(num)

    plt.plot(x_axis, solvertimelist, label="solver")
    plt.plot(x_axis, heurtimelist_latency, label="latency")
    plt.plot(x_axis, heurtimelist_weight, label="weight")
    plt.xlabel("Number of Nodes")
    plt.ylabel("Milliseconds")
    plt.title("Computation Time: Solver Vs Heuristic")
    plt.legend()
    plt.savefig("Computatoin Time", dpi=300)
    plt.show()


def draw_weightcomparison(
    nodes, heuravglist_latency, heuravglist_weight, solveravglist
):

    Y = heuravglist_latency
    Z = solveravglist
    W = heuravglist_weight

    X = list(range(nodes[0], nodes[1]))

    X_axis = np.arange(len(X))
    width = 0.25

    plt.bar(X_axis, Y, width, label="Latency Solution")
    plt.bar(X_axis + width, W, width, label="Weight Solution")
    plt.bar(X_axis + 2 * width, Z, width, label="Solver Solution")

    plt.xticks(X_axis, X)
    plt.xlabel("Nodes")
    plt.ylabel("NWeights")
    plt.title("Heuristic VS Solver (Sorted by latency)")
    plt.legend()
    plt.savefig("Weights comparision.png", dpi=300)
    plt.show()


def draw_errorplotweightplot(
    nodes,
    heuravglist_latency,
    heurstd_latency,
    heuravglist_weight,
    heurstd_weight,
    solveravglist,
    solstd,
):
    W = heuravglist_weight
    Y = heuravglist_latency
    Z = solveravglist
    Yerr = heurstd_latency
    Zerr = solstd
    Werr = heurstd_weight

    x_axis = np.linspace(nodes[0], nodes[1] - 1, nodes[1] - nodes[0])

    fig, ax = plt.subplots()

    ax.errorbar(x_axis, W, yerr=Werr, fmt="-o", label="weight")
    ax.errorbar(x_axis, Y, yerr=Yerr, fmt="-o", label="Latency")
    ax.errorbar(x_axis, Z, yerr=Zerr, fmt="-o", label="Solver")

    ax.set_xlabel("Nodes")
    ax.set_ylabel("Weight")
    ax.set_title("Weight plot with error bars")
    plt.legend()
    plt.savefig("errorbar.png", dpi=300)

    plt.show()


def graphgenerator():
    with open("../test/data/graphdata2.json") as f:
        file = json.load(f)
    solvertimelist = file["solvertimelist"]
    heurtimelist_latency = file["heurtimelist_latency"]
    heurtimelist_weight = file["heurtimelist_weight"]
    solveravglist = file["solveravglist"]
    heuravglist_latency = file["heuravglist_latency"]
    heuravglist_weight = file["heuravglist_weight"]
    heurstd_latency = file["heurstd_latency"]
    heurstd_weight = file["heurstd_weight"]
    solstd = file["solstd"]
    nodes = file["nodes"]

    draw_errorbar(
        nodes, heuravglist_latency, heurstd_latency, "Latenct Heuristic Std Error"
    )

    draw_errorbar(nodes, solveravglist, solstd, "SolverStd Error")

    draw_errorbar(
        nodes, heuravglist_weight, heurstd_weight, "Weight Heuristic Std Error"
    )

    draw_comparisiontime(
        nodes, solvertimelist, heurtimelist_latency, heurtimelist_weight
    )

    draw_weightcomparison(nodes, heuravglist_latency, heuravglist_weight, solveravglist)

    draw_errorplotweightplot(
        nodes,
        heuravglist_latency,
        heurstd_latency,
        heuravglist_weight,
        heurstd_weight,
        solveravglist,
        solstd,
    )


def test(latency, nodes, n, samplenumber, coefficient, bwlimit):
    data = []
    length = int(nodes[1] - nodes[0])
    for i in range(length):
        for c in range(samplenumber):
            answer = lbnxgraphgenerator(nodes[0] + i, 0.2, 1000, 20)
            check = answer[2]
            if not isinstance(check, str):
                # result = [latencyoutput,latencytime,weightoutput,weighttime]
                heur = answer[0]
                heurtime = answer[1]
                weight = answer[2]
                weighttime = answer[3]
                with open("./tests/data/LB_data.json") as f:
                    data = json.load(f)
                solveranswer = runMC_Solver(data)
                solver = solveranswer[0]
                solvertime = solveranswer[1]
                node = nodes[0] + i
                data.append(
                    [solver, heur, solvertime, heurtime, weight, weighttime, node, i]
                )
            else:
                data.append(
                    [solver, heur, solvertime, heurtime, weight, weighttime, node, i]
                )

    # print("data:"+str(data))
    solvertimelist = []
    heurtimelist_latency = []
    heurtimelist_weight = []
    solveravglist = []
    heuravglist_latency = []
    heuravglist_weight = []
    heurstd_latency = []
    heurstd_weight = []
    solstd = []

    for n in range(length):
        solvertime = []
        heurtime = []
        weighttime = []
        solversol = []
        heursol = []
        weightsol = []
        c = 0
        while c < samplenumber:
            solversol.append(data[n * samplenumber + c][0])
            heursol.append(data[n * samplenumber + c][1])
            solvertime.append(data[n * samplenumber + c][2])
            heurtime.append(data[n * samplenumber + c][3])
            weightsol.append(data[n * samplenumber + c][4])
            weighttime.append(data[n * samplenumber + c][5])
            c = c + 1
        solvertimelist.append(np.mean(solvertime))
        heurtimelist_latency.append(np.mean(heurtime))
        heurtimelist_weight.append(np.mean(weighttime))
        solveravglist.append(np.mean(solversol))
        heuravglist_latency.append(np.mean(heursol))
        heuravglist_weight.append(np.mean(weightsol))
        solstd.append(np.std(solversol))
        heurstd_latency.append(np.std(heursol))
        heurstd_weight.append(np.std(weightsol))

    file = {}
    file["solvertimelist"] = solvertimelist
    file["heurtimelist_latency"] = heurtimelist_latency
    file["heurtimelist_weight"] = heurtimelist_weight
    file["solveravglist"] = solveravglist
    file["heuravglist_latency"] = heuravglist_latency
    file["heuravglist_weight"] = heuravglist_weight
    file["heurstd_latency"] = heurstd_latency
    file["heurstd_weight"] = heurstd_weight
    file["solstd"] = solstd
    file["nodes"] = nodes

    filesave(file)
    graphgenerator()


#
# test(nodes=[18,21],n=0.2,samplenumber=10, coefficient=7,latency = 1000, bwlimit = 20)
#
