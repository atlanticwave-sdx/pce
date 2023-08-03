#!/bin/bash

#SBATCH --mail-type=begin,end,fail --mail-user=yxin@email.unc.edu
#SBATCH -p batch
#SBATCH --mem=128g
#SBATCH --time=0-12:00:00
#SBATCH --ntasks=2

#SBATCH --output=simulation.%A_%a.out
#SBATCH --error=simulation.%A_%a.error

#SBATCH --array=10-200:10

echo "My SLURM_ARRAY_TASK_ID: " $SLURM_ARRAY_TASK_ID
echo "Welcome $SLURM_ARRAY_TASK_ID times"
start=$(date +%s.%N)

python ./simulation.py -n 50 -m $SLURM_ARRAY_TASK_ID -p 0.2 -c 1 -b 1
	
duration=$(echo "$(date +%s.%N) - $start" | bc)
execution_time=`printf "%.2f seconds" $duration`

echo "Script Execution Time: $execution_time"

