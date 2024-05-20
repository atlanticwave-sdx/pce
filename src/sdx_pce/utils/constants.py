class Constants:
    BANDWIDTH = "bandwidth"
    ORIGINAL_BANDWIDTH = "original_bandwidth"
    LATENCY = "latency"
    PACKET_LOSS = "packet_loss"
    AVAILABILITY = "availability"
    WEIGHT = "weight"

    OBJECTIVE_COST = 0
    OBJECTIVE_LOAD_BALANCING = 1

    COST_FLAG_HOP = 0
    COST_FLAG_BW = 1
    COST_FLAG_LATENCY = 2
    COST_FLAG_RANDOM = 3
    COST_FLAG_STATIC = 4

    MIN_L_BW = 5000
    MAX_L_BW = 10000

    MIN_C_BW = 500
    MAX_C_BW = 1000

    MIN_L_LAT = 10
    MAX_L_LAT = 25

    ALPHA = 10 ^ 6

    DEFAULT_OWNER = "AmLight"
