#!/bin/bash

#SBATCH --mail-type=begin,end,fail --mail-user=yxin@email.unc.edu
#SBATCH -p batch
#SBATCH --mem=128g
#SBATCH --time=0-12:00:00
#SBATCH --ntasks=2

#SBATCH --output=heur.%A_%a.out
#SBATCH --error=heur.%A_%a.error

#SBATCH --array=0.5,1.0,1.5,2.0

echo "My SLURM_ARRAY_TASK_ID: " $SLURM_ARRAY_TASK_ID
echo "Welcome $SLURM_ARRAY_TASK_ID times"
start=$(date +%s.%N)

#python ./simulation.py -n 25 -m 200 -p 0.2 -c 1 -b 0 -heur 1 -a 0 -k $SLURM_ARRAY_TASK_ID
python ../src/sdx_pce/heuristic/heur.py -s $SLURM_ARRAY_TASK_ID -n ../src/sdx_pce/data/data/UsCarrier.json -a 21 -p 5 -g 1

duration=$(echo "$(date +%s.%N) - $start" | bc)
execution_time=`printf "%.2f seconds" $duration`

echo "Script Execution Time: $execution_time"