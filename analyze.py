import matplotlib.pyplot as plt
import numpy as np
import pickle
import sys
import argparse

parser = argparse.ArgumentParser(description='Plot the experimental results.')
parser.add_argument('-n_rep', '--n_rep', default=0, help="The number of repeted simulations for an experiment.", type=int)
parser.add_argument('-title', '--title', help="Plot title.",)
parser.add_argument('-baseline', '--baseline', default=0, help="With baseline (0: None, 1: VOTING)", type=int)

def plot_estimates(x_y_list, title, x=np.arange(10,1000,10)):

    estimates = []
    for x_y in x_y_list:
        y_ = []
        for x_ in x:
            y_.append(x_y[x_])
        estimates.append(y_)

    y = np.mean(estimates, axis=0)
    y_std = np.std(estimates, axis=0)

    plt.errorbar(x, y, yerr=y_std, fmt='o')
    plt.title(title)
    plt.xlabel('Num. assignments')
    plt.ylabel('Num. errors')
    plt.grid(True)
    plt.savefig('figs/estimates1.png')

def plot_with_baseline(x_y_list1, x_y_list2, title, labels=['T-WALK','VOTING'], x=np.arange(10,1000,10)):

    estimates1 = []
    for x_y in x_y_list1:
        y_ = []
        for x_ in x:
            y_.append(x_y[x_])
        estimates1.append(y_)

    estimates2 = []
    for x_y in x_y_list2:
        y_ = []
        for x_ in x:
            y_.append(x_y[x_])
        estimates2.append(y_)

    y1 = np.mean(estimates1, axis=0)
    y_std1 = np.std(estimates1, axis=0)
    y2 = np.mean(estimates2, axis=0)
    y_std2 = np.std(estimates2, axis=0)

    plt.errorbar(x, y1, yerr=y_std1, fmt='ro', label=labels[0])
    plt.errorbar(x, y2, yerr=y_std2, fmt='g^', label=labels[1])
    plt.title(title)
    plt.legend()
    plt.xlabel('Num. assignments')
    plt.ylabel('Num. errors')
    plt.grid(True)
    plt.savefig('figs/estimates2.png')
    
def main():
    args = parser.parse_args()
    n_rep = args.n_rep
    title = args.title
    baseline = args.baseline
    
    x_y_list = []
    if n_rep == 0:
        x_y = pickle.load(open('results/restaurant_estimates_real.p','rb'))
        print x_y
        x_y_list.append(x_y)
    else:
        for i in range(n_rep):
            x_y = pickle.load(open('results/restaurant_estimates_simulated%s.p'%i,'rb')) 
            x_y_list.append(x_y)

    plot_estimates(x_y_list, title, x=np.arange(10,len(x_y_list[0]),10))

    if baseline == 1:
        x_y_list2 = []
        for i in range(n_rep):
            x_y = pickle.load(open('results/restaurant_estimates_simulated_voting%s.p'%i,'rb')) 
            x_y_list2.append(x_y)

        plot_with_baseline(x_y_list, x_y_list2, title, ['T-WALK','VOTING'], x=np.arange(10,len(x_y_list[0]),10))

if __name__ == "__main__":
    main()
