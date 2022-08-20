#!/usr/bin/python3

from dataclasses import dataclass
import math

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
    PDiv1: int = 0
    PDiv2: int = 0
    PDiv3: int = 0
    N: int = 0
    M: int = 0
    P: int = 0
    N_p: int = 0
    Q: int = 0
    R: int = 0



# find valud 
def FindFrequency(f: PLL_Config):
    # make a list of possible VCO frequencies based on the output divider range
    valid_vco_freqs_y1 = []
    valid_vco_freqs_y2 = []
    valid_vco_freqs_y3 = []

    f.f_out2 = f.f_out1 if f.f_out2 <= 0 else f.f_out2
    f.f_out3 = f.f_out1 if f.f_out3 <= 0 else f.f_out3

    # the search range can be narrowed by knowing the VCO range and output frequency
    # so we only need to search around f_vco_max/f_out to f_vco_min/f_out
    # but for now just search the entire range
    # TODO: split into function
    # TODO: trick: Y1 can be bypass
    for pd in range(1,128):
        # early return; if it's already below minimum then it'll only get worse if we keep going
        if (f.f_out1 * pd)>=f.f_vco_max:
            break;
        if (f.f_out1 * pd)<=f.f_vco_max:
            valid_vco_freqs_y1.append(pd*f.f_out1)
    for pd in range(1,128):
        if (f.f_out2 * pd)>=f.f_vco_max:
            break;
        if (f.f_out2 * pd)<=f.f_vco_max:
            valid_vco_freqs_y2.append(pd*f.f_out2)
    for pd in range(1,128):
        if (f.f_out3 * pd)>=f.f_vco_max:
            break;
        if (f.f_out3 * pd)<=f.f_vco_max:
            valid_vco_freqs_y3.append(pd*f.f_out3)
    #print ("Plausible VCO frequencies Y1: " + str(valid_vco_freqs_y1))
    #print ("Plausible VCO frequencies Y2: " + str(valid_vco_freqs_y2))
    # find the common values
    valid_vco_freqs = list(set(valid_vco_freqs_y1) & set(valid_vco_freqs_y2) & set(valid_vco_freqs_y3))
    valid_vco_freqs.sort(reverse=True)

    #print ("Plausible combination is: " + str(valid_vco_freqs))
    valid_dividers = []

    # for each probable VCO frequency, calculate the N/M values that can reach this
    # ClockPro seems to like high values for N/M, so we do a reverse search
    # it also tends to prefer higher VCO frequencies so we start with the highest valid one    
    foundvalid = False
    for vcofreq in valid_vco_freqs:
        for m in range (511,0,-1):
            if foundvalid == True:
                break
            for n in range (4095,0,-1):
                if (f.f_in * (n/m) == vcofreq):
                    # calculate the value of P/Q/R and see if the combo is valid
                    p_prime = CalcPQR(n,m)
                    if (p_prime[3] == True):
                        valid_dividers.append((n,m, p_prime,vcofreq))
                        # early return
                        foundvalid = True
                    break
    if len(valid_dividers) == 0:
        print("No valid combination found")
        return
    f.f_vco = valid_dividers[0][3]
    f.N = valid_dividers[0][0]
    f.M = valid_dividers[0][1]
    f.P = valid_dividers[0][2][0]
    f.Q = valid_dividers[0][2][1]
    f.R = valid_dividers[0][2][2]
    f.PDiv1 = int(f.f_vco/f.f_out1)
    f.PDiv2 = int(f.f_vco/f.f_out2)
    f.PDiv3 = int(f.f_vco/f.f_out3)

    if valid_dividers[0][2][3] == True:
        print(f)
    


g = PLL_Config(f_in=10e6, f_out1=24.576e6, f_out2=2.048e6)

FindFrequency(g)