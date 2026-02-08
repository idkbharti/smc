"""
Original Pine Script:
export storeOrderBlock(Pivot p_ivot, bool internal, int bias, Settings settings, array<OrderBlock> internalOrderBlocks, array<OrderBlock> swingOrderBlocks, array<float> parsedHighs, array<float> parsedLows, array<int> times) =>
    if (not internal and settings.showSwingOrderBlocksInput) or (internal and settings.showInternalOrderBlocksInput)
        array<float> a_rray = na
        int parsedIndex = na

        if bias == BEARISH
            a_rray := parsedHighs.slice(p_ivot.barIndex, bar_index)
            parsedIndex := p_ivot.barIndex + a_rray.indexof(a_rray.max())
        else
            a_rray := parsedLows.slice(p_ivot.barIndex, bar_index)
            parsedIndex := p_ivot.barIndex + a_rray.indexof(a_rray.min())

        OrderBlock o_rderBlock = OrderBlock.new(parsedHighs.get(parsedIndex), parsedLows.get(parsedIndex), times.get(parsedIndex), bias)
        array<OrderBlock> orderBlocks = internal ? internalOrderBlocks : swingOrderBlocks

        if orderBlocks.size() >= 100
            orderBlocks.pop()
        orderBlocks.unshift(o_rderBlock)
"""

from typing import List
from ..smc_types import Pivot, Settings, OrderBlock
from ..constants import BEARISH, BULLISH

def store_order_block(pivot: Pivot, internal: bool, bias: int, settings: Settings, 
                      internal_order_blocks: List[OrderBlock], swing_order_blocks: List[OrderBlock], 
                      parsed_highs: List[float], parsed_lows: List[float], times: List[int], current_index: int):
    """
    Identifies and stores an Order Block based on recent pivot and price action.
    
    Args:
        pivot: The pivot point that triggered the structure.
        internal: Boolean, true if internal structure.
        bias: BEARISH or BULLISH.
        settings: Settings object.
        internal_order_blocks: List to store internal OBs.
        swing_order_blocks: List to store swing OBs.
        parsed_highs: Historical highs.
        parsed_lows: Historical lows.
        times: Historical times.
        current_index: Current bar index.
    """
    
    # Check if OBs are enabled for this type
    if (not internal and settings.showSwingOrderBlocksInput) or (internal and settings.showInternalOrderBlocksInput):
        
        # We need to find the extreme candle between the pivot and current time.
        # Pivot bar index vs current bar index.
        # Note: `parsedHas` is presumably indexed by bar_index (or mapped 1:1).
        # We assume parsedHighs[i] corresponds to bar_index=i.
        
        start_index = pivot.barIndex
        end_index = current_index
        
        # Safety check for slice
        if start_index >= len(parsed_highs) or end_index >= len(parsed_highs):
            return # Should not happen if history is synced
            
        # Get the slice of interest
        # array.slice(start, end) includes start, excludes end? Pine: "slice(from, to) -> The 'to' index is exclusive."
        # Wait, Pine slice `to` is exclusive.
        # In Python slice [start:end] is exclusive.
        # So logic aligns.
        
        relevant_highs = parsed_highs[start_index : end_index]
        relevant_lows = parsed_lows[start_index : end_index]
        
        target_index = -1
        
        if bias == BEARISH:
            # Find the highest candle in the range (supply zone responsible for break)
            # Pine: parsedIndex := p_ivot.barIndex + a_rray.indexof(a_rray.max())
            if not relevant_highs: return
            max_val = max(relevant_highs)
            offset = relevant_highs.index(max_val)
            target_index = start_index + offset
        else: # BULLISH
            # Find the lowest candle (demand zone)
            if not relevant_lows: return
            min_val = min(relevant_lows)
            offset = relevant_lows.index(min_val)
            target_index = start_index + offset
            
        # Create OrderBlock object
        if target_index >= 0 and target_index < len(times):
            ob = OrderBlock(
                barHigh = parsed_highs[target_index],
                barLow = parsed_lows[target_index],
                barTime = times[target_index],
                bias = bias
            )
            
            target_list = internal_order_blocks if internal else swing_order_blocks
            
            # Manage size
            if len(target_list) >= 100:
                target_list.pop() # Remove last (oldest) - Pine: array.pop() removes last element
            
            target_list.insert(0, ob) # Add to front (newest) - Pine: array.unshift()
