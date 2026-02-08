"""
This file contains the class definitions (Types) used in the SMC library.
It mirrors the 'export type' definitions from the original Pine Script.
"""

from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Alerts:
    """
    Holds boolean flags for all possible alert conditions.
    Original Pine Script:
    export type Alerts
        bool internalBullishBOS = false
        ...
    """
    internalBullishBOS: bool = False
    internalBearishBOS: bool = False
    internalBullishCHoCH: bool = False
    internalBearishCHoCH: bool = False
    swingBullishBOS: bool = False
    swingBearishBOS: bool = False
    swingBullishCHoCH: bool = False
    swingBearishCHoCH: bool = False
    internalBullishOrderBlock: bool = False
    internalBearishOrderBlock: bool = False
    swingBullishOrderBlock: bool = False
    swingBearishOrderBlock: bool = False
    equalHighs: bool = False
    equalLows: bool = False
    bullishFairValueGap: bool = False
    bearishFairValueGap: bool = False

@dataclass
class TrailingExtremes:
    """
    Tracks the highest and lowest points of the most recent swing.
    Original Pine Script:
    export type TrailingExtremes
        float top
        float bottom
    """
    top: float = 0.0
    bottom: float = 0.0
    barTime: int = 0
    barIndex: int = 0
    lastTopTime: int = 0
    lastBottomTime: int = 0

@dataclass
class FairValueGap:
    """
    Stores information about a Fair Value Gap (FVG).
    """
    top: float = 0.0
    bottom: float = 0.0
    bias: int = 0
    # Box references are visual, skipping for core logic or using placeholders
    topBox: Optional[object] = None
    bottomBox: Optional[object] = None

@dataclass
class Trend:
    """
    Simple wrapper to store the current trend direction.
    """
    bias: int = 0

@dataclass
class EqualDisplay:
    """
    Stores the visual elements for Equal Highs/Lows.
    """
    l_ine: Optional[object] = None
    l_abel: Optional[object] = None

@dataclass
class Pivot:
    """
    Represents a significant high or low point (Swing Point).
    Original Pine Script:
    export type Pivot
        float currentLevel
        float lastLevel
        bool crossed
    """
    currentLevel: float = float('nan')
    lastLevel: float = float('nan')
    crossed: bool = False
    barTime: int = 0
    barIndex: int = 0

@dataclass
class OrderBlock:
    """
    Stores details of an Order Block candle.
    """
    barHigh: float = 0.0
    barLow: float = 0.0
    barTime: int = 0
    bias: int = 0

@dataclass
class Settings:
    """
    Aggregates all user input values to be passed to functions.
    """
    # Colors (stored as hex strings or generic objects for now)
    swingBullishColor: str = "#000000"
    swingBearishColor: str = "#000000"
    fairValueGapBullishColor: str = "#000000"
    fairValueGapBearishColor: str = "#000000"
    premiumZoneColor: str = "#000000"
    discountZoneColor: str = "#000000"
    internalBullishOrderBlockColor: str = "#000000"
    internalBearishOrderBlockColor: str = "#000000"
    swingBullishOrderBlockColor: str = "#000000"
    swingBearishOrderBlockColor: str = "#000000"
    
    # Toggles & Values
    showSwingsInput: bool = False
    showStructureInput: bool = False
    showInternalsInput: bool = False
    showTrendInput: bool = False
    showHighLowSwingsInput: bool = False
    showPremiumDiscountZonesInput: bool = False
    showEqualHighsLowsInput: bool = False
    showFairValueGapsInput: bool = False
    showInternalOrderBlocksInput: bool = False
    showSwingOrderBlocksInput: bool = False
    
    equalHighsLowsThresholdInput: float = 0.1
    equalHighsLowsSizeInput: str = "tiny"
    modeInput: str = "Historical"
    internalStructureSize: str = "tiny"
    swingStructureSize: str = "small"
    
    # Logic Settings
    internalFilterConfluenceInput: bool = False
    showInternalBullInput: str = "All"
    showInternalBearInput: str = "All"
    showSwingBullInput: str = "All"
    showSwingBearInput: str = "All"
    
    internalOrderBlocksSizeInput: int = 5
    swingOrderBlocksSizeInput: int = 5
    orderBlockMitigationInput: str = "High/Low"
    
    fairValueGapsExtendInput: int = 1
    fairValueGapsThresholdInput: bool = True
    fairValueGapsTimeframeInput: str = ""
