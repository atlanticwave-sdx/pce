""" Slurm cluster
Python 3.8 and above
"""
unc vpn

ssh

cd ~/pce

----Longleaf.unc.edu---
module load anaconda

conda env list
conda create -n my_env python=3.8
conda activate my_env


---ht1.renci.org---
sinteractive
module load python/3.10.0
pip install -r requirements.txt 
export PYTHONPATH=$PYTHONPATH:$PWD/src
sbatch --mail-type=begin --mail-type=end --mail-type=fail --mail-user=yxin@email.unc.edu -p general -N 1 --mem=128g -n 1 -c 12 -t 5- --wrap="python ./simulation.py -m 200"

(sbatch --mail-type=begin --mail-type=end --mail-type=fail --mail-user=yxin@email.unc.edu -p batch -N 1 --mem=128g -n 1 -c 12 -t 5- --wrap="python ./simulation.py -m 3" )

sbatch --mail-type=begin --mail-type=end --mail-type=fail --mail-user=yxin@email.unc.edu -p batch -N 1 --mem=128g -n 1 -c 12 -t 5- --wrap="python ./simulation.py -m 100 -p 0.2 -c 1 -b 1 "

scancel 5544939510
```

sbatch simulation_job.sh


