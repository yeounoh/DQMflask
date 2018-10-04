# Data Quality Metric (DQM) over Python Flask
Estimating the number of remaining errors (aka Data Quality Metric/`DQM`) in a dataset is an important problem. Previously (http://www.vldb.org/pvldb/vol10/p1094-chung.pdf), we have shown that some heuristic estimators can provide useful estimates to guide the data cleaning process (e.g., know when to stop cleaning). 

## System Overview
We simulate a data error detection experiment using crowds. One of the key design goals was to dynamically render the task page on AMT, according to the current estimation status. That is, we pose new questions to the next worker based on the previous responses we've collected. This is different from actual data cleaning nor other estimation scenarios where we pre-define all the random batches to render the task page.

This enables more efficient estimation (in terms of the number of worker responses, a.k.a. assignments); however, such as, this is much slower in wall-clock time. To speed up the estimation process, as well as to reduce the estimation bias, we run multiple independent tracks of experiments, of which we average the results. To further optimize the run-time, we load-balance the incoming worker traffics to the multiple tracks/experiments.

The simulator runs with a Python Flask server, running locally. This becomes handy when we run real experiments using Amazon Mechanical Turks.

## Setup
* Clone this repository: `git clone https://github.com/yeounoh/DQMflask.git`.
* Start Python `virtualenv` with Python 2 (https://help.dreamhost.com/hc/en-us/articles/215489338-Installing-and-using-virtualenv-with-Python-2).
* Run `pip install -r requirements.txt` in the cloned local git repo.

## Running The Server
```python
python main.py
```

## Running The Client
The simulator is implemented in `simulation.py`. It has a number of simulation parameters:
```python
python simulation.py -h
usage: simulation.py [-h] [-assignment NUM_ASSIGNMENTS] [-hits NUM_HITS]
                     [-n_max N_MAX] [-n_rep N_REP] [-w WORKER_QUALITY]
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
  -n_rep N_REP, --n_rep N_REP
                        Simulation repetetions
  -w WORKER_QUALITY, --worker_quality WORKER_QUALITY
                        Worker quality (default=1.0)
  -est_type ESTIMATOR_TYPE, --estimator_type ESTIMATOR_TYPE
                        Estimation technique (default=0) 0: TriangularWalk, 1:
                        VOTING, 2: SWITCH
```

For instance, to simulate an estimation using Triangular Walk algorithm (`est_type 0`) with 10 HITs (also 10 tracks of independent experiments), 60 assignments per HIT, run the following command.
```python
python simulation.py -assignment 60 -hits 5 -n_max 20 -n_rep 5 -est_type 0
```
The `n_max` flag sets the depth of the triangle for the algorithm, and `n_rep` the number of simulation repetetions. Similarly, we can also run a baseline, majority voting estimation (`est_type 1`).
```python
python simulation.py -assignment 60 -hits 5 -n_max 20 -n_rep 5 -est_type 1
```

You can plot the results by running `analyze.py`:
```python
python analyze.py -h
usage: analyze.py [-h] [-n_rep N_REP] [-title TITLE] [-baseline BASELINE]
                  [-x X_MAX]

Plot the experimental results.

optional arguments:
  -h, --help            show this help message and exit
  -n_rep N_REP, --n_rep N_REP
                        The number of repeted simulations for an experiment.
  -title TITLE, --title TITLE
                        Plot title.
  -baseline BASELINE, --baseline BASELINE
                        With baseline (0: None, 1: VOTING, 2: VOTING & SWITCH)
  -x X_MAX, --x_max X_MAX
                        the maximum x (number of assignment) range for
                        plotting (deafult 1000)
```

```python
python analyze.py -n_rep 5 -baseline 1 -title "5 HITs * 60 Assignments/HIT / n_max=20"
```

![picture alt](https://github.com/yeounoh/DQMflask/blob/master/5h_60a_20m_v.png "Simulation Result")


