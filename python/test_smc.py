import random
import math
from smc_logic import SMCLogic

def generate_sine_wave_data(length=200):
    """
    Generates synthetic OHLCV data using a sine wave to create clear swings.
    """
    data = []
    for i in range(length):
        # Base price using a sine wave + trend
        trend = i * 0.1
        wave = math.sin(i * 0.1) * 10
        price = 100 + trend + wave
        
        # Simulate OHLC around the price
        open_p = price + random.uniform(-1, 1)
        close_p = price + random.uniform(-1, 1)
        high_p = max(open_p, close_p) + random.uniform(0, 2)
        low_p = min(open_p, close_p) - random.uniform(0, 2)
        
        data.append({
            'time': i,
            'open': open_p,
            'high': high_p,
            'low': low_p,
            'close': close_p,
            'volume': 1000
        })
    return data

def main():
    print("Generating Synthetic Data...")
    df = generate_sine_wave_data(300)
    
    print("Initializing SMC Logic...")
    smc = SMCLogic()
    
    print("Running Logic...")
    events = smc.get_structure(df, size=5)
    
    print("\n--- RESULTS ---")
    if not events:
        print("No structure events detected.")
    else:
        for e in events:
            if e['event']:
                print(f"Bar {e['bar_index']}: {e['event']}")

main()
