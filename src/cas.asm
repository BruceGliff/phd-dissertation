  # a0 -- address of memory location
  # a1 -- expected value
  # a2 -- desired value
  # a0 -- return value
cas:
  lr.w t0, (a0)
  bne t0, a1, fail
  sc.w t0, a2, (a0)
  bnez t0, cas
  li a0, 0
  jr ra
fail:
  li a0, 1
  jr ra
