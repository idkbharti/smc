"""
Original Pine Script:
export startOfNewLeg(int leg) => ta.change(leg) != 0
export startOfBearishLeg(int leg) => ta.change(leg) == -1
export startOfBullishLeg(int leg) => ta.change(leg) == +1
"""

def start_of_new_leg(current_leg: int, previous_leg: int) -> bool:
    """
    Checks if the leg direction has changed.
    Pine `ta.change(leg)` returns `current - previous`.
    `!= 0` means they are different.
    """
    return current_leg != previous_leg

def start_of_bearish_leg(current_leg: int, previous_leg: int) -> bool:
    """
    Checks if the leg has switched to bearish.
    in Pine: `ta.change(leg) == -1` -> `current - previous == -1`
    Implies `previous` was 1 (BULLISH) and `current` is 0 (BEARISH).
    Assuming BULLISH_LEG=1, BEARISH_LEG=0.
    """
    # Using the constants from constants.py would be safer, but logic holds.
    # 0 - 1 = -1
    return (current_leg - previous_leg) == -1

def start_of_bullish_leg(current_leg: int, previous_leg: int) -> bool:
    """
    Checks if the leg has switched to bullish.
    in Pine: `ta.change(leg) == +1` -> `current - previous == +1`
    Implies `previous` was 0 (BEARISH) and `current` is 1 (BULLISH).
    """
    return (current_leg - previous_leg) == 1
