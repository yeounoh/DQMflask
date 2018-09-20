import numpy as np
import math

def check_triangle_completion(n_, k_, n_max=50):

    estimate_ = 0.
    if n_ < n_max and k_/n_ > 0.5:
        return False, estimate_
    else:
        if k_/n_ <= 0.5:
            return True, estimate_
        if (2-n_max-2*k_)**2 -4*(2*n_max-2)*k_ >= 0:
            p_ = ( 2.*k_+n_max-2+math.sqrt((2-n_max-2*k_)**2-4*(2*n_max-2)*k_)) / (4.*n_max-4)
        else:
            p_ = ((2.*k_+n_max-2)/(4*n_max-4))
        p_ = max(p_, 0.6)
        estimate_ = 1./(2*p_-1.) - 0.165*p_*(1-p_)/(2*p_ - 1)**2

        return True, estimate_