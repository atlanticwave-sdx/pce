import re

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator


# Function to read
# last N lines of the file
def last_n_lines(fname, n):
    # opening file using with() method
    # so that file get closed
    # after completing work
    results = None
    try:
        with open(fname) as file:

            # loop to read iterate
            # last n lines and convert to a dict
            results = {}
            for line in file.readlines()[-n:]:
                # print(line, end ='')
                list = re.split(", |=|;|:|\+", line.splitlines()[0])
                it = iter(list)
                res_dct = dict(zip(it, it))
                results = {**results, **res_dct}
            results["Script Execution Time"] = results["Script Execution Time"].split()[
                0
            ]
            print(results)
    except IOError as e:
        print(e)
    return results


def plot_heur(path, title, tag):
    n = 5
    num_connection_list = []

    time_list_dict = {}
    total_util_list_dict = {}
    max_util_list_dict = {}
    mean_util_list_dict = {}
    std_util_list_dict = {}
    ninetypercetile_util_list_dict = {}
    objective_list_dict = {}

    for dir, name in title.items():
        time_list = []
        total_util_list = []
        max_util_list = []
        mean_util_list = []
        std_util_list = []
        ninetypercetile_util_list = []
        objective_list = []

        key = re.split(r"\D+", dir)[1]
        if key == "0":
            key = "Linear Partition"
        if key == "1":
            key = "Geometry Partition"
        if key == "2":
            key = "K-Way Partition"
        print("key=" + key)

        time_list_dict[key] = time_list
        total_util_list_dict[key] = total_util_list
        max_util_list_dict[key] = max_util_list
        mean_util_list_dict[key] = mean_util_list
        std_util_list_dict[key] = std_util_list
        ninetypercetile_util_list_dict[key] = ninetypercetile_util_list
        objective_list_dict[key] = objective_list

        for i in (2, 4, 8, 10, 16, 20):
            fname = path + dir + name + str(i) + ".out"
            results = last_n_lines(fname, n)
            if results is not None:
                if "Script Execution Time" in results.keys():
                    time_list.append(float(results["Script Execution Time"]))
                else:
                    time_list.append(None)
                if "total_util" in results.keys():
                    total_util_list.append(float(results["total_util"]))
                else:
                    total_util_list.append(None)
                if "max_util" in results.keys():
                    max_util_list.append(float(results["max_util"]))
                else:
                    max_util_list.append(None)
                if "mean_util" in results.keys():
                    mean_util_list.append(float(results["mean_util"]))
                else:
                    mean_util_list.append(None)
                if "std_util" in results.keys():
                    std_util_list.append(float(results["std_util"]))
                else:
                    std_util_list.append(None)
                if "ninetypercetile_util" in results.keys():
                    ninetypercetile_util_list.append(
                        float(results["ninetypercetile_util"])
                    )
                else:
                    ninetypercetile_util_list.append(None)
                if "Objective value " in results.keys():
                    objective_list.append(float(results["Objective value "]))
                else:
                    objective_list.append(None)
            else:
                time_list.append(None)
                total_util_list.append(None)
                max_util_list.append(None)
                mean_util_list.append(None)
                std_util_list.append(None)
                ninetypercetile_util_list.append(None)
                objective_list.append(None)
    # print(results)
    num_connection_list = [2, 4, 8, 10, 16, 20]
    y_label = [
        "Computation Time (s)",
        "Total Utility",
        "Max Utility",
        "Mean Utility",
        "STD Utility",
        "90% Utility",
        "Objective value",
    ]
    x_label = "Number of Groups"

    fig1, ax1 = plt.subplots()
    ax1.set_title(y_label[0])
    ax1.set_xlabel(x_label)
    for key in time_list_dict.keys():
        ax1.plot(num_connection_list, time_list_dict[key], label=str(key))

    ax1.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    name = y_label[0] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig2, ax2 = plt.subplots()
    ax2.set_title(y_label[1])
    ax2.set_xlabel(x_label)
    for key in total_util_list_dict.keys():
        ax2.plot(num_connection_list, total_util_list_dict[key], label=str(key))

    ax2.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    name = y_label[1] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")
    ax2.legend()

    fig3, ax3 = plt.subplots()
    ax3.set_title(y_label[2])
    ax3.set_xlabel(x_label)
    for key in max_util_list_dict.keys():
        ax3.plot(num_connection_list, max_util_list_dict[key], label=str(key))

    ax3.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    name = y_label[2] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig4, ax4 = plt.subplots()
    ax4.set_title(y_label[3])
    ax4.set_xlabel(x_label)
    for key in mean_util_list_dict.keys():
        ax4.plot(num_connection_list, mean_util_list_dict[key], label=str(key))
    ax4.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    name = y_label[3] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig5, ax5 = plt.subplots()
    ax5.set_title(y_label[4])
    ax5.set_xlabel(x_label)
    for key in std_util_list_dict.keys():
        ax5.plot(num_connection_list, std_util_list_dict[key], label=str(key))
    ax5.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    name = y_label[4] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig6, ax6 = plt.subplots()
    ax6.set_title(y_label[5])
    ax6.set_xlabel(x_label)
    ax6.set_ylim([0.99999, 1.0])
    for key in ninetypercetile_util_list_dict.keys():
        print(ninetypercetile_util_list_dict[key])
        ax6.plot(
            num_connection_list, ninetypercetile_util_list_dict[key], label=str(key)
        )
    ax6.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    name = y_label[5] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig7, ax7 = plt.subplots()
    ax7.set_title(y_label[6])
    ax7.set_xlabel(x_label)
    for key in objective_list_dict.keys():
        ax7.plot(num_connection_list, objective_list_dict[key], label=str(key))
    ax7.xaxis.set_major_locator(MaxNLocator(integer=True))
    plt.legend()
    name = y_label[6] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")


# Driver Code:
if __name__ == "__main__":
    path = "../../tests/results/"
    # title= {'out_heur_0_10_28_200/':"heur.57344567_",
    #        'out_heur_1_10_28_200/':"heur.57346971_",
    #        'out_heur_2_10_28_200/':"heur.57362683_"
    #        }
    # tag=' Heur 200'

    # title= {'out_heur_0_25_10_28_100/':"heur.57930569_",
    #        'out_heur_1_25_10_28_100/':"heur.57613457_",
    #        'out_heur_2_25_10_28_100/':"heur.57931558_"
    #        }
    # tag=' Heur 100'

    title = {
        "out_heur_0_0_25_10_28_200/": "heur.58150822_",
        "out_heur_1_0_25_10_28_200/": "heur.58081157_",
        "out_heur_2_0_25_10_28_200/": "heur.58082696_",
    }
    tag = "MC Heur 200 "

    plot_heur(path, title, tag)
