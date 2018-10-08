import numpy as np
import math

default_coeff = {
    8: 0,
    9: 6.91310814435742,
    10: 5.03184709494337,
    11: 2.10144000103314,
    12: 0.635599038344795,
    13: 1.96455080814112,
    14: 1.01560222816783,
    15: 1.00912038379987,
}

def check_triangle_completion(n_, k_, n_max=15, coefficients=default_coeff):
    if n_ < n_max and k_*1./n_ > 0.5:
        return False, 0.
    else:
        if k_*1./n_ <= 0.5:
            return True, 0.
        else:
            return True, coefficients[k_]
