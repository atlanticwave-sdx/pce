#! /bin/bash

echo "Simulation of tunnel TE varying the solver and scale" 

for g in 0 1
do
    echo $g
    for a in 20 21 10 11
    do
        echo $a
        for s in 0.5 1 1.5 2
        do
            echo $s
            python ../src/sdx_pce/heuristic/heur.py -n ../src/sdx_pce/data/data/UsCarrier.json -a $a -p 5 -s $s -g $g
        done
    done
done