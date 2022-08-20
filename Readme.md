# CDCE913 Calculator
A script to calculate the PLL coefficients for a given set of output frequencies.

The goal is to make a script that can generate a binary blob or C-includes to program the CDCE913 to an arbitrary frequency. The algorithm is potentially intended for embedded use so I'm trying to remove any dynamic allocation requirements.

Currently it is capable of calculating coefficients for a given input frequency and up to three outputs. It does not support approximate frequencies yet - i.e. it has to find an exact match given the inputs and outputs.

Bypassing the VCO is done automatically for Y1 if no VCO solution was found.

In my limited testing it appears to yield the same values as ClockPro version 1.2.1.