import json

data = [
    {
        "1": [[1, 9], [9, 11]],
        "2": [[3, 1], [1, 12], [12, 0], [0, 18]],
        "3": [[2, 12], [12, 16], [16, 9], [9, 13]],
    },
    14195698.0,
]
with open("test_HeurCSP_solution.json", "w") as json_file:
    json.dump(data, json_file, indent=4)
