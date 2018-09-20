# Data Quality Metric (DQM) over Python Flask
Estimating the number of remaining errors (aka Data Quality Metric/`DQM`) in a dataset is an important problem. Previously (http://www.vldb.org/pvldb/vol10/p1094-chung.pdf), we have shown that some heuristic estimators can provide useful estimates to guide the data cleaning process (e.g., know when to stop cleaning). 

This work implements a simulator for selected estimation techniques.

# Overview
We simulate a data error detection experiment using crowds. One of the key design goals was to dynamically render the task page on AMT, according to the current estimation status. That is, we pose new questions to the next worker based on the previous responses we've collected. This is different from actual data cleaning nor other estimation scenarios where we pre-define all the random batches to render the task page.

This enables more efficient estimation (in terms of the number of worker responses, a.k.a. assignments); however, such as, this is much slower in wall-clock time. To speed up the estimation process, as well as to reduce the estimation bias, we run multiple independent tracks of experiments, of which we average the results. To further optimize the run-time, we load-balance the incoming worker traffics to the multiple tracks/experiments.

The simulator runs with a Python Flask server, running locally. This becomes handy when we run real experiments using Amazon Mechanical Turks.

# Setup & Install Dependencies
* Clone this git repo: `git clone https://github.com/yeounoh/DQMflask.git`.
* Start Python `virtualenv` with Python 2 (https://help.dreamhost.com/hc/en-us/articles/215489338-Installing-and-using-virtualenv-with-Python-2).
* Run `pip install -r requirements.txt` in the cloned local git repo.

# Running The Server
```python
python main.py
```

# Running The Client
```python
python simulation.py -h
usage: simulation.py [-h] [-assignment NUM_ASSIGNMENTS] [-hits NUM_HITS]
                     [-n_max N_MAX] [-qsize QUEUE_SIZE] [-n_rep N_REP]
                     [-est_type ESTIMATOR_TYPE]

Simulated Triangular Walk Experiment.

optional arguments:
  -h, --help            show this help message and exit
  -assignment NUM_ASSIGNMENTS, --num_assignments NUM_ASSIGNMENTS
                        Number of assignments per HIT
  -hits NUM_HITS, --num_hits NUM_HITS
                        Number of HITs
  -n_max N_MAX, --n_max N_MAX
                        Triangle depth
  -qsize QUEUE_SIZE, --queue_size QUEUE_SIZE
                        Server-side priority queue size
  -n_rep N_REP, --n_rep N_REP
                        Simulation repetetions
  -est_type ESTIMATOR_TYPE, --estimator_type ESTIMATOR_TYPE
                        Estimation technique (default=0) 0: TriangularWalk, 1:
                        VOTING
```

## Amazon Mechanical Turks Expeirments
`amt/` folder contains codes for AMT experiments. The experiments (data cleaning or error detection) were crowdsourced on AMT.
```python
python amt/exp_restaurant_dataset.py
```
