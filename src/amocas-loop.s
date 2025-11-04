# a1 -- memory location
# a2 -- expected value
# a3 -- desired value
label:
  amocas.w.rl.aq  a2, a3, (a1)
  bne a2, a3, label
