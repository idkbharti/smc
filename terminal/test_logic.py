class OB:
    def __init__(self, low, high):
        self.low = low
        self.high = high
        self.cur_l = low
        self.partial = False
        self.mitigated = False

ob = OB(100, 110)
candles = [
    (90, 95, 92),  # L, H, C -> no tap
    (90, 102, 95), # taps low -> entry 1. cur_l = 102
    (90, 101, 95), # inside mitigated area -> no entry
    (90, 105, 95), # deeper tap -> entry 2. cur_l = 105
    (90, 115, 95), # full mitigation -> entry 3. mitigated = True
]

trades = []
for i, (l, h, c) in enumerate(candles):
    if ob.mitigated: continue
    if h > ob.high:
        if h > ob.cur_l:
            trades.append((i, "trade full", c))
        ob.mitigated = True
    elif h > ob.cur_l:
        trades.append((i, "trade partial", c))
        ob.cur_l = h
        ob.partial = True

print(trades)
