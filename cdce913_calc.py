#!/usr/bin/python3

from dataclasses import dataclass
import math
import time

# calculate PLL tuning values for the CDCE913
# based on datasheet section 9.2.2.2
# the end goal is to make a binary blob that can be written to the chip

# f_vco = f_in * N/M
# where f_vco 80..230 MHz
# f_out = f_vco/Pdiv
# where M 1..511 and N 1..4095, Pdiv 1..127

# also calculate internals
# P = max(4-int(log2(N/M)),0)
#  Text: P 0..4
#  Table 12: P 0..7
# N'=max(N*2^P, M) (this is not used by the hardware)
# Q = int(N'/M)
#   Q 16..63
# R = N'-(M*Q)
#  Text: R 0..51
#  Table 12: R 0..511
# ClockPro uses the extended range listed in Table 12

def CalcPQR(N,M):
    # P = max(4-int(log2(N/M)),0)
    #   P 0..4
    P = max(4-int(math.log2(N/M)),0)
    pvalid = True if (P<=7) else False

    N_p = max(N*math.pow(2,P),M)
    Q=int(N_p/M)
    qvalid = True if (Q<=63 and Q>=16) else False
    R=int((N_p-(M*Q)))
    rvalid = True if (R>=0 and R<=511) else False



    if pvalid and qvalid and rvalid:
        return (P, Q, R, True)
    else:
        return (P, Q, R, False)

@dataclass
class PLL_Config:
    f_in: float = 0.0
    f_vco: float = 0.0
    f_vco_min = 80e6
    f_vco_max = 230e6
    f_out1: float = 0.0
    f_out2: float = 0.0
    f_out3: float = 0.0
    f_error1: float = 0.0 # not supported currently, we only do exact frequencies
    f_error2: float = 0.0
    f_error3: float = 0.0
    Y1bypass: bool = False
    PDiv1: int = 0
    PDiv2: int = 0
    PDiv3: int = 0
    N: int = 0
    M: int = 0
    P: int = 0
    Q: int = 0
    R: int = 0

# search for a valid N/M set, by searching the range of M values
# if N = M*(vcofreq/fin) is an integer then we have a match
# and we can check it for validity
def FindPLLParms(fin: float, vcofreq:float):
    foundvalid = False
    ratio = vcofreq/fin

    for m in range (1,512):
        n = m*ratio
        if n == int(n) and n<=4095:
            n = int(n)
            p_prime = CalcPQR(n,m)
            if (p_prime[3] == True):
                return((n,m, p_prime,vcofreq))
    return False

# it can be implemented without dynamic memory allocations and only gives a single result
# TODO: we also need to check if (Y2 AND Y3) can be solved with a submultiple of f_in, bypassing the VCO core
def FindFrequency_FirstServed(f: PLL_Config):
    f.f_out2 = f.f_out1 if f.f_out2 <= 0 else f.f_out2
    f.f_out3 = f.f_out2 if f.f_out3 <= 0 else f.f_out3

    # calculate the possible range of PDs for each output
    if f.Y1bypass:
        pd1_min = int(f.f_in/f.f_out1)
        pd1_max = pd1_min
    else:
        pd1_min = int(max(math.floor(f.f_vco_min/f.f_out1), 1))
        pd1_max = int(min(math.ceil(f.f_vco_max/f.f_out1), 127))
    pd2_min = int(max(math.floor(f.f_vco_min/f.f_out2), 1))
    pd2_max = int(min(math.ceil(f.f_vco_max/f.f_out2), 127))
    pd3_min = int(max(math.floor(f.f_vco_min/f.f_out3), 1))
    pd3_max = int(min(math.ceil(f.f_vco_max/f.f_out3), 127))

    # search for the first valid and highest VCO frequency that matches all output
    # we start at the top since ClockPro seems to do this
    for pd3 in range(pd3_max, pd3_min-1, -1):
        for pd2 in range(pd2_max, pd2_min-1, -1):
            for pd1 in range(pd1_max, pd1_min-1, -1):
                y1vco = f.f_out1 * pd1
                y2vco = f.f_out2 * pd2
                y3vco = f.f_out3 * pd3
                if f.Y1bypass and pd1*f.f_out1 == f.f_in:
                    y1vco = y2vco
                    
                if y1vco == y2vco and y1vco == y3vco:
                    pllparms = FindPLLParms(f.f_in, y3vco)
                    if not pllparms:
                        break
                    else:
                        f.f_vco = pllparms[3]
                        f.N = pllparms[0]
                        f.M = pllparms[1]
                        f.P = pllparms[2][0]
                        f.Q = pllparms[2][1]
                        f.R = pllparms[2][2]
                        f.PDiv1 = pd1
                        f.PDiv2 = pd2
                        f.PDiv3 = pd3
                        print(f)
                        return
    # recursiveish
    if not f.Y1bypass:
        f.Y1bypass = True
        FindFrequency_FirstServed(f)
    else:
        print("No match found")
    return

                    


g = PLL_Config(f_in=19.2e6, f_out1=19.2e6, f_out2=22.1184e6)

print()
st = time.process_time_ns()
FindFrequency_FirstServed(g)
et = time.process_time_ns()
res = et - st
print('FindFrequency_FirstServed took:', res/1e6, ' ms') # this gives a 0 result on Windows 10 - real fast?