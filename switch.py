import numpy as np
import copy


def vNominal(data):
    return np.sum(np.sum(data==1, axis=1) > np.sum(data != -1, axis=1)/2)

def sNominal(data,pos_switch=True,neg_switch=True):
    data_subset = data # no copying
    majority = np.zeros((len(data_subset),len(data_subset[0])))
    switches = np.zeros((len(data_subset),len(data_subset[0])))
    for i in range(len(data_subset)):
        prev = 0
        for w in range(0,len(data_subset[0])):
            # the first worker is compared with an algorithmic worker
            n_w = np.sum(data[i][0:w+1] != -1)
            n_pos = np.sum(data[i][0:w+1] == 1)
            n_neg = np.sum(data[i][0:w+1] == 0)

            maj = 0
            if n_pos == n_neg and n_pos != 0:
                # tie results in switch
                maj = (prev + 1)%2
            elif n_pos > n_w/2:
                maj = 1
            if prev != maj:
                if (maj == 1 and pos_switch) or (maj == 0 and neg_switch):
                    switches[i][w] = 1
            prev = maj
            majority[i][w] = maj

    return np.sum(np.logical_and(np.sum(switches,axis=1), np.sum(data,axis=1) != -1*len(data[0])))

def remain_switch(data, pos_switch=True, neg_switch=True):
    data_subset = copy.deepcopy(data)
    majority = np.zeros((len(data_subset),len(data_subset[0])))
    switches = np.zeros((len(data_subset),len(data_subset[0])))
    for i in range(len(data_subset)):
        prev = 0
        for w in range(0,len(data_subset[0])):
            # the first worker is compared with an algorithmic worker
            n_w = np.sum(data[i][0:w+1] != -1)
            n_pos = np.sum(data[i][0:w+1] == 1)
            n_neg = np.sum(data[i][0:w+1] == 0)

            maj = 0
            if n_pos == n_neg and n_pos != 0:
                # tie results in switch
                maj = (prev + 1)%2
            elif n_pos > n_w/2:
                maj = 1
            if prev != maj:
                if (maj == 1 and pos_switch) or (maj == 0 and neg_switch):
                    switches[i][w] = 1
            prev = maj
            majority[i][w] = maj

    n_worker = np.sum(data_subset != -1, axis=1)
    n_all = n_worker
    data_subset[data_subset == -1] = 0

    histogram = n_worker
    n = float(np.sum(n_worker))
    n_bar = float(np.mean(n_worker))
    v_bar = float(np.var(n_worker))
    d = np.sum(np.logical_and(np.sum(switches,axis=1), n_all != 0))
    if n == 0:
        return d

    f1 = 0.
    for i in range(len(switches)):
        if n_worker[i] == 0:
            continue
        for k in range(len(switches[0])):
            j = len(switches[0]) -1 - k
            if data[i][j] == -1:
                continue
            elif switches[i][j] == 1:
                f1 += 1
            break

    # remove no-ops
    for i in range(len(switches)):
        switch_idx= np.where(switches[i,:]==1)[0]
        if len(switch_idx) > 0:
            n -= np.sum(data[i,:np.amin(switch_idx)] != -1)
        elif len(switch_idx) == 0:
            n -= np.sum(data[i,:] != -1)
    if n == 0:
        return d

    c_hat = max(1. - f1/n, 0.)
    if c_hat == 0.:
        return d

    gamma = v_bar/n_bar

    est = d/c_hat + n*(1-c_hat)/c_hat*gamma

    return est

"""
    Switch-based estimator 
"""
def switch(data):
    n_worker = len(data[0])
    est = vNominal(data)
    thresh = np.max([vNominal(data[:,:n_worker/2]),
                     vNominal(data[:,:n_worker/4]),
                     vNominal(data[:,:n_worker/4*3]) ])
    pos_adj = 0
    neg_adj = 0
    if est - thresh < 0:
        neg_adj = max(0,
                      remain_switch(
                        data,pos_switch=False,neg_switch=True)
                        - sNominal(data,pos_switch=False,neg_switch=True)
                      )
    else:
        pos_adj = max(0,
                      remain_switch(
                        data,pos_switch=True,neg_switch=False)
                        - sNominal(data,pos_switch=True,neg_switch=False)
                      )

    return max(0, est + pos_adj - neg_adj)
    