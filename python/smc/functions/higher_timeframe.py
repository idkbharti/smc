"""
Original Pine Script:
export higherTimeframe(string timeframe) => timeframe.in_seconds() > timeframe.in_seconds(timeframe)
"""

def higher_timeframe(current_timeframe: str, target_timeframe: str) -> bool:
    """
    Checks if `target_timeframe` is higher (longer duration) than `current_timeframe`.
    
    Args:
        current_timeframe: String e.g., "1m", "1h", "1D".
        target_timeframe: String e.g., "4h", "1W".
        
    Returns:
        True if target is higher, False otherwise.
    """
    # Simple heuristic for now, can be expanded strictly if needed.
    # Map to minutes
    def to_minutes(tf: str) -> int:
        if not tf: return 0
        if tf.endswith('S'): return 1 # Treat seconds as minute fraction? Placeholder.
        if tf.endswith('D'): return int(tf[:-1]) * 1440
        if tf.endswith('W'): return int(tf[:-1]) * 10080
        if tf.endswith('M'): return int(tf[:-1]) * 43200
        # Default assumes minutes if number or ends in 'm' (Pine often uses just numbers for minutes)
        if tf.isdigit(): return int(tf)
        return int(tf) if tf.isdigit() else 0

    return to_minutes(target_timeframe) > to_minutes(current_timeframe)
