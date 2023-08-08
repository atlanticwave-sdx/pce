import re

import matplotlib.pyplot as plt


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
                list = re.split(r", |=|;|:|\+", line.splitlines()[0])
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


def plot_simulation(path, title):
    tag = " Simulation"
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
        print("key=" + key)

        time_list_dict[key] = time_list
        total_util_list_dict[key] = total_util_list
        max_util_list_dict[key] = max_util_list
        mean_util_list_dict[key] = mean_util_list
        std_util_list_dict[key] = std_util_list
        ninetypercetile_util_list_dict[key] = ninetypercetile_util_list
        objective_list_dict[key] = objective_list

        for i in range(10, 210, 10):
            fname = path + dir + name + str(i) + ".out"
            results = last_n_lines(fname, n)
            if results is not None:
                time_list.append(float(results["Script Execution Time"]))
                total_util_list.append(float(results["total_util"]))
                max_util_list.append(float(results["max_util"]))
                mean_util_list.append(float(results["mean_util"]))
                std_util_list.append(float(results["std_util"]))
                ninetypercetile_util_list.append(float(results["ninetypercetile_util"]))
                objective_list.append(float(results["Objective value "]))
            else:
                time_list.append(None)
                total_util_list.append(None)
                max_util_list.append(None)
                mean_util_list.append(None)
                std_util_list.append(None)
                ninetypercetile_util_list.append(None)
                objective_list.append(None)

    num_connection_list = [*range(10, 210, 10)]
    y_label = [
        "Compuation Time (s)",
        "Total Utility",
        "Max Utility",
        "Mean Utility",
        "STD Utility",
        "90% Utility",
        "Objective value",
    ]
    x_label = "Number of Connections"

    fig1, ax1 = plt.subplots()
    ax1.set_title(y_label[0])
    ax1.set_xlabel(x_label)
    for key in time_list_dict.keys():
        ax1.plot(num_connection_list, time_list_dict[key], label=str(key))
    # ax1.plot(num_connection_list,time_list, label = 'N=25')

    plt.legend()
    name = y_label[0] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig2, ax2 = plt.subplots()
    ax2.set_title(y_label[1])
    ax2.set_xlabel(x_label)
    for key in total_util_list_dict.keys():
        ax2.plot(num_connection_list, total_util_list_dict[key], label=str(key))

    plt.legend()
    name = y_label[1] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")
    ax2.legend()

    fig3, ax3 = plt.subplots()
    ax3.set_title(y_label[2])
    ax3.set_xlabel(x_label)
    for key in max_util_list_dict.keys():
        ax3.plot(num_connection_list, max_util_list_dict[key], label=str(key))

    plt.legend()
    name = y_label[2] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig4, ax4 = plt.subplots()
    ax4.set_title(y_label[3])
    ax4.set_xlabel(x_label)
    for key in mean_util_list_dict.keys():
        ax4.plot(num_connection_list, mean_util_list_dict[key], label=str(key))
    plt.legend()
    name = y_label[3] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig5, ax5 = plt.subplots()
    ax5.set_title(y_label[4])
    ax5.set_xlabel(x_label)
    for key in std_util_list_dict.keys():
        ax5.plot(num_connection_list, std_util_list_dict[key], label=str(key))
    plt.legend()
    name = y_label[4] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig6, ax6 = plt.subplots()
    ax6.set_title(y_label[5])
    ax4.set_xlabel(x_label)
    for key in ninetypercetile_util_list_dict.keys():
        ax6.plot(
            num_connection_list, ninetypercetile_util_list_dict[key], label=str(key)
        )
    plt.legend()
    name = y_label[5] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig7, ax7 = plt.subplots()
    ax7.set_title(y_label[6])
    ax4.set_xlabel(x_label)
    for key in objective_list_dict.keys():
        ax7.plot(num_connection_list, objective_list_dict[key], label=str(key))
    plt.legend()
    name = y_label[6] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")


def plot_heur(title, path):
    tag = "heur"

    num_connection_list = []
    time_list = []
    weight_list = []
    util_list = []
    max_util_list = []
    for i in (2, 4, 8, 10):
        name = path + title + str(i) + ".out"
        num_connection_list.append(i)
        results = last_n_lines(name, 2)
        time_list.append(float(results["Script Execution Time"]))
        weight_list.append(float(results["total_weight"]))
        util_list.append(float(results["total_util"]))
        max_util_list.append(float(results["max_util"]))

    y_label = ["Compuation Time (s)", "Total Weight", "Total Utility", "Max Utility"]
    x_label = "Number of Groups"
    fig1, ax1 = plt.subplots()
    ax1.set_title(y_label[0])
    ax1.set_xlabel(x_label)
    # for key in score_dict.keys():
    #    ax1.plot(missing_rate_list,score_dict[key], label = str(key))
    ax1.plot(num_connection_list, time_list, label="N=25")

    plt.legend()
    name = y_label[0] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig2, ax2 = plt.subplots()
    ax2.set_title(y_label[1])
    ax2.set_xlabel(x_label)
    # for key in rmse_dict.keys():
    #    ax2.plot(missing_rate_list,rmse_dict[key], label = str(key))
    print(weight_list)
    ax2.plot(num_connection_list, weight_list, label="N=25")

    plt.legend()
    name = y_label[1] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig3, ax3 = plt.subplots()
    ax3.set_title(y_label[2])
    ax3.set_xlabel(x_label)
    # for key in mse_dict.keys():
    #    ax3.plot(missing_rate_list,mse_dict[key], label = str(key))
    ax3.plot(num_connection_list, util_list, label="N=25")
    print(util_list)

    plt.legend()
    name = y_label[2] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")

    fig4, ax4 = plt.subplots()
    ax4.set_title(y_label[3])
    ax4.set_xlabel(x_label)
    # for key in mse_dict.keys():
    #    ax3.plot(missing_rate_list,mse_dict[key], label = str(key))
    ax4.plot(num_connection_list, max_util_list, label="N=25")
    print(max_util_list)

    plt.legend()
    name = y_label[3] + tag + ".png"
    plt.savefig(name, bbox_inches="tight")


# Driver Code:
if __name__ == "__main__":
    # fname = '/Users/yxin/NSF/aw-sdx/sdx_pce/tests/results/simulation.57036414_10.out'
    # N = 2
    # LastNlines(fname, N)
    path = "../../tests/results/"
    title = {
        "out_simulation_50_10_28/": "simulation.57510402_",
        "out_simulation_25_10_28_200/": "simulation.57466833_",
    }
    plot_simulation(path, title)

    # title = "heur.57082350_"
    # path = '../../tests/results/out_heur_10_25/'
    # plot_heur(title,path)
