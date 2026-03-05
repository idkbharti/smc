//@version=5
indicator('Advanced Pine', 'Advanced Pine', overlay = true, max_labels_count = 500, max_lines_count = 500)

//-----------------------------------------------------------------------------
// Inputs
//-----------------------------------------------------------------------------
insideColor             = input.color(color.new(color.blue, 0), "Inside Candle Color")
showStructureInput      = input(true, "Show Swing Structure")
showHighLowSwingsInput  = input(true, "Show Strong/Weak High/Low")

swingsLengthInput       = input.int(50, "Swing Structure Length", minval=10)

//-----------------------------------------------------------------------------
// Constants & Types
//-----------------------------------------------------------------------------
COLOR_BLACK = color.black
BULLISH     = 1
BEARISH     = -1

type pivot
    float currentLevel
    float lastLevel
    bool crossed
    int barTime
    int barIndex

type trailingExtremes
    float top
    float bottom
    int barTime
    int barIndex
    int lastTopTime
    int lastBottomTime

type trend
    int bias

//-----------------------------------------------------------------------------
// Variables
//-----------------------------------------------------------------------------
var pivot swingHigh                 = pivot.new(na, na, false, 0, 0)
var pivot swingLow                  = pivot.new(na, na, false, 0, 0)
var trailingExtremes trailing       = trailingExtremes.new(na, na, 0, 0, 0, 0)
var trend swingTrend                = trend.new(0)

//-----------------------------------------------------------------------------
// Calculations - Inside Candle
//-----------------------------------------------------------------------------
isInside = high < high[1] and low > low[1]
barcolor(isInside ? insideColor : na)

//-----------------------------------------------------------------------------
// Functions
//-----------------------------------------------------------------------------
leg(int size) =>
    var leg = -1
    if high[size] > ta.highest(size)
        leg := 0 // Bearish leg starts (found High)
    else if low[size] < ta.lowest(size)
        leg := 1 // Bullish leg starts (found Low)
    leg

updateTrailingExtremes() =>
    trailing.top            := math.max(high, trailing.top)
    trailing.lastTopTime    := trailing.top == high ? time : trailing.lastTopTime
    trailing.bottom         := math.min(low, trailing.bottom)
    trailing.lastBottomTime := trailing.bottom == low ? time : trailing.lastBottomTime

startOfNewLeg(int leg)      => ta.change(leg) != 0
startOfBearishLeg(int leg)  => leg == 0 and leg[1] != 0
startOfBullishLeg(int leg)  => leg == 1 and leg[1] != 1

// Convert raw timeframe.period string to a TradingView-style label
// e.g. "240" → "4H", "60" → "1H", "15" → "15m", "D" → "1D"
formatTF(string tf) =>
    switch tf
        "1"   => "1m"
        "2"   => "2m"
        "3"   => "3m"
        "5"   => "5m"
        "10"  => "10m"
        "15"  => "15m"
        "20"  => "20m"
        "30"  => "30m"
        "45"  => "45m"
        "60"  => "1H"
        "120" => "2H"
        "180" => "3H"
        "240" => "4H"
        "360" => "6H"
        "480" => "8H"
        "720" => "12H"
        "D"   => "1D"
        "W"   => "1W"
        "M"   => "1M"
        => tf  // fallback for any unlisted timeframe

getAutoLTF() =>
    switch timeframe.period
        "15"  => "5"
        "60"  => "15"
        "D"   => "60"
        => ""

//-----------------------------------------------------------------------------
// Logic - Swing Structure
//-----------------------------------------------------------------------------
getCurrentStructure(int size) =>
    currentLeg              = leg(size)
    newPivot                = startOfNewLeg(currentLeg)
    pivotLow                = startOfBullishLeg(currentLeg)
    pivotHigh               = startOfBearishLeg(currentLeg)

    if newPivot
        if swingTrend.bias == 0
            swingTrend.bias := pivotLow ? BULLISH : BEARISH

        if pivotLow
            swingLow.lastLevel      := swingLow.currentLevel
            swingLow.currentLevel   := low[size]
            swingLow.crossed        := false
            swingLow.barTime        := time[size]
            swingLow.barIndex       := bar_index[size]
            
            // Sync trailing
            trailing.bottom         := swingLow.currentLevel
            trailing.barTime        := swingLow.barTime
            trailing.barIndex       := swingLow.barIndex
            trailing.lastBottomTime := swingLow.barTime

        else
            swingHigh.lastLevel     := swingHigh.currentLevel
            swingHigh.currentLevel  := high[size]
            swingHigh.crossed       := false
            swingHigh.barTime       := time[size]
            swingHigh.barIndex      := bar_index[size]

            // Sync trailing
            trailing.top            := swingHigh.currentLevel
            trailing.barTime        := swingHigh.barTime
            trailing.barIndex       := swingHigh.barIndex
            trailing.lastTopTime    := swingHigh.barTime

    swingTrend.bias

drawStructure(pivot p_ivot, string tag, color structureColor, string lineStyle, string labelStyle, string labelSize) =>    
    var line l_ine      = line.new(na,na,na,na,xloc = xloc.bar_time)
    var label l_abel    = label.new(na,na)

    // Historical Logic
    l_ine   := line.new(chart.point.new(p_ivot.barTime,na,p_ivot.currentLevel), chart.point.new(time,na,p_ivot.currentLevel), xloc.bar_time, color=structureColor, style=lineStyle)
    l_abel  := label.new(chart.point.new(na,math.round(0.5*(p_ivot.barIndex+bar_index)),p_ivot.currentLevel), tag, xloc.bar_index, color=color(na), textcolor=structureColor, style=labelStyle, size = labelSize)

displayStructure() =>
    
    // Bullish Break
    if ta.crossover(close, swingHigh.currentLevel) and not swingHigh.crossed
        string tag = swingTrend.bias == BEARISH ? 'CHoCH' : 'BOS'
        swingTrend.bias   := BULLISH
        swingHigh.crossed := true

        if showStructureInput
            drawStructure(swingHigh, tag, COLOR_BLACK, line.style_solid, label.style_label_down, size.small)

    // Bearish Break
    if ta.crossunder(close, swingLow.currentLevel) and not swingLow.crossed
        string tag = swingTrend.bias == BULLISH ? 'CHoCH' : 'BOS'
        swingTrend.bias   := BEARISH
        swingLow.crossed  := true

        if showStructureInput
            drawStructure(swingLow, tag, COLOR_BLACK, line.style_solid, label.style_label_up, size.small)

//-----------------------------------------------------------------------------
// Execution
//-----------------------------------------------------------------------------
if showHighLowSwingsInput
    updateTrailingExtremes()

getCurrentStructure(swingsLengthInput)

// Snapshot crossed-flags BEFORE displayStructure() sets them to true.
// We use these snapshots in the OB section below to detect fresh BOS/CHoCH events.
_obPreHighCrossed = swingHigh.crossed
_obPreLowCrossed  = swingLow.crossed

displayStructure()

//-----------------------------------------------------------------------------
// Strong/Weak High/Low Lines
//-----------------------------------------------------------------------------
var line highLine       = line.new(na, na, na, na, xloc=xloc.bar_time, color=COLOR_BLACK)
var line lowLine        = line.new(na, na, na, na, xloc=xloc.bar_time, color=COLOR_BLACK)
// style_label_lower_right: anchor is the right end of the line; text extends LEFT → visually end-aligned
var label highLabel     = label.new(na, na, text="", xloc=xloc.bar_time, color=color(na), textcolor=COLOR_BLACK, style=label.style_label_lower_right, size=size.small)
var label lowLabel      = label.new(na, na, text="", xloc=xloc.bar_time, color=color(na), textcolor=COLOR_BLACK, style=label.style_label_upper_right, size=size.small)

if showHighLowSwingsInput
    barDuration  = time - time[1]
    rightTimeBar = last_bar_time + 20 * barDuration
    tf_str       = formatTF(timeframe.period)  // e.g. "4H", "15m", "1D"

    if not na(trailing.top)
        bool isStrongHigh = swingTrend.bias == BEARISH
        line.set_xy1(highLine,    trailing.lastTopTime, trailing.top)
        line.set_xy2(highLine,    rightTimeBar, trailing.top)
        line.set_style(highLine,  isStrongHigh ? line.style_solid : line.style_dashed)
        label.set_xy(highLabel,   rightTimeBar, trailing.top)
        label.set_text(highLabel, (isStrongHigh ? 'Strong High' : 'Weak High') + ' · ' + tf_str)

    if not na(trailing.bottom)
        bool isStrongLow = swingTrend.bias == BULLISH
        line.set_xy1(lowLine,    trailing.lastBottomTime, trailing.bottom)
        line.set_xy2(lowLine,    rightTimeBar, trailing.bottom)
        line.set_style(lowLine,  isStrongLow ? line.style_solid : line.style_dashed)
        label.set_xy(lowLabel,   rightTimeBar, trailing.bottom)
        label.set_text(lowLabel, (isStrongLow ? 'Strong Low' : 'Weak Low') + ' · ' + tf_str)

//-----------------------------------------------------------------------------
// Trend Display Logic
//-----------------------------------------------------------------------------
// Isolated logic for security to avoid side-effect errors
calcTrendForSecurity(int size) =>
    // Define local state isolated from the main chart
    var pivot sHigh = pivot.new(na, na, false, 0, 0)
    var pivot sLow  = pivot.new(na, na, false, 0, 0)
    var trend sTrend = trend.new(0)
    
    // We can reuse the helper functions as they don't modify globals
    currentLeg = leg(size)
    newPivot   = startOfNewLeg(currentLeg)
    pivotLow   = startOfBullishLeg(currentLeg)
    
    if newPivot
        // Infer trend if Neutral
        if sTrend.bias == 0
            sTrend.bias := pivotLow ? BULLISH : BEARISH
            
        if pivotLow
            sLow.lastLevel      := sLow.currentLevel
            sLow.currentLevel   := low[size]
            sLow.crossed        := false
            // Note: We don't need to track barTime/Index for trend bias calculation
            // checking 'crossover' or 'crossunder' logic for BOS/CHoCH might require level history
            
        else
            sHigh.lastLevel     := sHigh.currentLevel
            sHigh.currentLevel  := high[size]
            sHigh.crossed       := false

    // BOS/CHoCH Logic (Simplified for Trend Bias)
    // Bullish Break
    if ta.crossover(close, sHigh.currentLevel) and not sHigh.crossed
        sTrend.bias     := BULLISH
        sHigh.crossed   := true

    // Bearish Break
    if ta.crossunder(close, sLow.currentLevel) and not sLow.crossed
        sTrend.bias     := BEARISH
        sLow.crossed    := true
            
    sTrend.bias

// Fetch the 15m, 1H, Daily bias. 'barmerge.lookahead_off' ensures no repainting.
int tf15_trend = request.security(syminfo.tickerid, "15", calcTrendForSecurity(swingsLengthInput), lookahead = barmerge.lookahead_off)
int tf1H_trend = request.security(syminfo.tickerid, "60", calcTrendForSecurity(swingsLengthInput), lookahead = barmerge.lookahead_off)
int tfD_trend  = request.security(syminfo.tickerid, "D",  calcTrendForSecurity(swingsLengthInput), lookahead = barmerge.lookahead_off)

// Display Table (columns: 0=15m, 1=1H, 2=Daily)
var table trendTable = table.new(position.top_right, 3, 1, border_width = 1)

// Helper: bg color based on trend, text is just the timeframe
trendText(int bias, string label) =>
    color bg = bias == BULLISH ? color.new(color.green, 70) : bias == BEARISH ? color.new(color.red, 70) : color.new(color.gray, 70)
    [label, bg]

if barstate.islast
    [tf15Text, tf15Bg] = trendText(tf15_trend, "15m")
    table.cell(trendTable, 0, 0, tf15Text, bgcolor = tf15Bg, text_color = color.black, text_size = size.small)

    [tf1HText, tf1HBg] = trendText(tf1H_trend, "1H")
    table.cell(trendTable, 1, 0, tf1HText, bgcolor = tf1HBg, text_color = color.black, text_size = size.small)

    [tfDText, tfDBg] = trendText(tfD_trend, "1D")
    table.cell(trendTable, 2, 0, tfDText,  bgcolor = tfDBg,  text_color = color.black, text_size = size.small)

//=============================================================================
// ORDER BLOCKS  (ported from LuxAlgo Smart Money Concepts)
//=============================================================================

//-----------------------------------------------------------------------------
// OB Inputs
//-----------------------------------------------------------------------------
grpOB = "Order Blocks"

showSwingOBInput    = input.bool(true,  "Show Swing OBs",        group = grpOB, inline = "sob")
swingOBOutsideCountInput = input.int( 1, "Outside OB Count", group = grpOB, inline = "sob", minval = 0, maxval = 10)
showInternalOBInput = input.bool(true,  "Show Internal OBs",     group = grpOB, inline = "iob")
internalOBOutsideCountInput = input.int( 1, "Outside OB Count", group = grpOB, inline = "iob", minval = 0, maxval = 10)
showRefinedOBInput  = input.bool(true,  "Show Refined OB",       group = grpOB, tooltip="Automatically refines OBs to lower timeframes: (15m->5m), (1H->15m), (1D->1H).")
alertRefinedOBInput = input.bool(false, "Alert when Refined OB is Tapped", group = grpOB, tooltip="Triggers a TradingView alert whenever price first taps a Refined OB. Use 'Any alert() function call' in your TV alert settings.")

obTrendFilterInput  = input.bool(false, "Filter OB by Trend",    group = grpOB, tooltip="If disabled, shows both Bullish and Bearish OBs regardless of the current trend.")

obFilterInput       = input.string("Atr", "OB Filter",           group = grpOB, options = ["Atr","Cumulative Mean Range"],
     tooltip = "ATR: skip candles wider than 2×ATR (high-volatility). Cumulative Mean Range: uses rolling average true range.")
obMitigationInput   = input.string("High/Low", "OB Mitigation",  group = grpOB, options = ["Close","High/Low"],
     tooltip = "Price source used to determine when an OB is invalidated (mitigated).")

swingBullOBColor    = input.color(color.new(#1848cc, 93), "Swing Bullish OB",   group = grpOB)
swingBearOBColor    = input.color(color.new(#b22833, 93), "Swing Bearish OB",   group = grpOB)
intBullOBColor      = input.color(color.new(#3179f5, 93), "Internal Bullish OB",group = grpOB)
intBearOBColor      = input.color(color.new(#f77c80, 93), "Internal Bearish OB",group = grpOB)

//-----------------------------------------------------------------------------
// OB Type
//-----------------------------------------------------------------------------
// Represents a single order block candle
type orderBlock
    float barHigh       // high of the OB candle
    float barLow        // low  of the OB candle
    int   barTime       // time of the OB candle
    int   bias          // BULLISH (+1) or BEARISH (-1)
    bool  partial = false // true when price has entered the zone but not fully broken it
    bool  mitigated = false // true when price has fully broken the zone
    int   mitigationTime = 0 // time when the OB was mitigated
    bool  isRefined = false
    string refinedTag = ""

//-----------------------------------------------------------------------------
// OB Storage Arrays
//-----------------------------------------------------------------------------
// Each swing BOS/CHoCH stores a new OB; mitigated ones are discarded.
var array<orderBlock> swingOBs    = array.new<orderBlock>()
var array<orderBlock> internalOBs = array.new<orderBlock>()
var array<orderBlock> refinedOBs  = array.new<orderBlock>()

// Parallel arrays of boxes AND labels for efficient `set_*` updates (created once at bar 0)
var array<box>   swingOBBoxes    = array.new<box>()
var array<box>   internalOBBoxes = array.new<box>()
var array<label> swingOBLabels    = array.new<label>()
var array<label> internalOBLabels = array.new<label>()

// We now dynamically size arrays below as needed in drawOBs, 
// so we don't prepopulate `_i to N` boxes and labels here anymore.

//-----------------------------------------------------------------------------
// OB Volatility Filter  (mirrors LuxAlgo)
//-----------------------------------------------------------------------------
// Volatile candles are excluded from being picked as the OB candle.
// Instead their opposite extreme is used (parsedHigh / parsedLow arrays).
ob_atrMeasure    = ta.atr(200)
ob_volatility    = obFilterInput == "Atr" ? ob_atrMeasure : ta.cum(ta.tr) / bar_index
ob_highVolBar    = (high - low) >= 2 * ob_volatility

// "Parsed" high/low: if volatile, flip to opposite extreme; otherwise keep as-is
ob_parsedHigh    = ob_highVolBar ? low  : high
ob_parsedLow     = ob_highVolBar ? high : low

// Rolling arrays — we need history to look back from pivot to current bar
var array<float> ob_parsedHighs = array.new<float>()
var array<float> ob_parsedLows  = array.new<float>()
var array<float> ob_highs       = array.new<float>()
var array<float> ob_lows        = array.new<float>()
var array<int>   ob_times       = array.new<int>()

ob_parsedHighs.push(ob_parsedHigh)
ob_parsedLows.push(ob_parsedLow)
ob_highs.push(high)
ob_lows.push(low)
ob_times.push(time)

//-----------------------------------------------------------------------------
// OB Mitigation Sources
//-----------------------------------------------------------------------------
ob_bearMitigationSrc = obMitigationInput == "Close" ? close : high
ob_bullMitigationSrc = obMitigationInput == "Close" ? close : low

//-----------------------------------------------------------------------------
// [LEGACY - kept for reference, no longer called]
// storeOB_legacy()  ─ OLD approach: on every BOS/CHoCH, scan the whole range
//   from pivot.barIndex → bar_index and pick the single best candle:
//     • BULLISH OB → lowest parsedLow in range (demand candle)
//     • BEARISH OB → highest parsedHigh in range (supply candle)
//   Limitation: does not validate that the selected candle actually swept
//   liquidity or that a Fair Value Gap existed after it.
//-----------------------------------------------------------------------------
storeOB_legacy(pivot p_ivot, bool internal, int bias) =>
    bool show = internal ? showInternalOBInput : showSwingOBInput

    if show
        array<float> arr  = na
        int parsedIdx     = na

        if bias == BEARISH
            // Bearish OB: highest parsed high between pivot bar and now
            arr       := ob_parsedHighs.slice(p_ivot.barIndex, bar_index)
            parsedIdx := p_ivot.barIndex + arr.indexof(arr.max())
        else
            // Bullish OB: lowest parsed low between pivot bar and now
            arr       := ob_parsedLows.slice(p_ivot.barIndex, bar_index)
            parsedIdx := p_ivot.barIndex + arr.indexof(arr.min())

        orderBlock ob = orderBlock.new(
             ob_parsedHighs.get(parsedIdx),
             ob_parsedLows.get(parsedIdx),
             ob_times.get(parsedIdx),
             bias)

        array<orderBlock> obs = internal ? internalOBs : swingOBs

        // Cap the array to avoid unbounded growth
        if obs.size() >= 100
            obs.pop()
        obs.unshift(ob)

//-----------------------------------------------------------------------------
// deleteOBs()  ─ remove OBs whose price level has been mitigated (breached)
//-----------------------------------------------------------------------------
deleteOBs(int obType) =>
    array<orderBlock> obs = obType == 1 ? internalOBs : swingOBs

    int i = obs.size() - 1
    while i >= 0
        orderBlock ob = obs.get(i)

        if ob.bias == BEARISH
            // Full mitigation: price fully above OB high
            if ob_bearMitigationSrc > ob.barHigh
                obs.remove(i)
            // Partial mitigation: price entered the OB zone (above low, not yet above high)
            else if ob_bearMitigationSrc > ob.barLow
                if not ob.partial and ob.isRefined and alertRefinedOBInput
                    alert("Bearish Refined OB Tapped on " + syminfo.tickerid + " (" + ob.refinedTag + ")", alert.freq_once_per_bar_close)
                ob.partial := true

        else if ob.bias == BULLISH
            // Full mitigation: price fully below OB low
            if ob_bullMitigationSrc < ob.barLow
                obs.remove(i)
            // Partial mitigation: price entered the OB zone (below high, not yet below low)
            else if ob_bullMitigationSrc < ob.barHigh
                if not ob.partial and ob.isRefined and alertRefinedOBInput
                    alert("Bullish Refined OB Tapped on " + syminfo.tickerid + " (" + ob.refinedTag + ")", alert.freq_once_per_bar_close)
                ob.partial := true

        i -= 1

//-----------------------------------------------------------------------------
// drawOBs()  ─ paint the top-N OBs as boxes extending to the right
//-----------------------------------------------------------------------------
drawOBs(int obType) =>
    array<orderBlock> obs    = obType == 1 ? internalOBs : swingOBs
    array<box>        boxes  = obType == 1 ? internalOBBoxes : swingOBBoxes
    array<label>      labels = obType == 1 ? internalOBLabels : swingOBLabels
    int outsideOBMax         = obType == 1 ? internalOBOutsideCountInput : swingOBOutsideCountInput
    int obsSize              = obs.size()
    bool internal            = obType == 1

    // ── Range: current Strong Low ↔ Strong/Weak High (using trailing extremes)
    float zoneTop    = trailing.top    // Weak or Strong High level
    float zoneBottom = trailing.bottom // Weak or Strong Low level

    // Match the same right-side endpoint used by Strong/Weak High/Low lines
    int ob_rightTime = last_bar_time + 20 * (time - time[1])

    if obsSize > 0
        // Current timeframe string for the inline OB label (e.g. "15", "5", "D")
        string tf_tag = formatTF(timeframe.period)  // e.g. "4H", "15m", "1D"
        // ── Build filtered list: all in-range OBs + N above + N below ────────
        array<orderBlock> inRange = array.new<orderBlock>()
        array<orderBlock> aboveOBs = array.new<orderBlock>()
        array<orderBlock> belowOBs = array.new<orderBlock>()

        // obs is sorted newest-first; iterate all
        for ob in obs
            ob_inZone = ob.barLow < zoneTop and ob.barHigh > zoneBottom
            if ob_inZone
                inRange.push(ob)
            else if ob.barLow >= zoneTop
                // OB is above range — collect them
                aboveOBs.push(ob)
            else if ob.barHigh <= zoneBottom
                // OB is below range — collect them
                belowOBs.push(ob)

        // Sort above/below to find the closest ones
        // Above OBs: closest means lowest barLow. We want ascending order of barLow.
        // Hand-rolling simple selection since PineScript array sorting algorithms don't directly work on custom type properties well without custom map/sort.
        // For simplicity we will pick the nearest N.
        array<orderBlock> closestAboveOBs = array.new<orderBlock>()
        int aboveCount = aboveOBs.size() > 0 and outsideOBMax > 0 ? math.min(aboveOBs.size(), outsideOBMax) : 0
        if aboveCount > 0
            for i = 1 to aboveCount
                orderBlock closest = na
                int closestIdx = -1
                for j = 0 to aboveOBs.size() - 1
                    orderBlock candidate = aboveOBs.get(j)
                    if closestIdx == -1
                        closest := candidate
                        closestIdx := j
                    else if candidate.barLow < closest.barLow
                        closest := candidate
                        closestIdx := j
                if closestIdx != -1
                    closestAboveOBs.push(closest)
                    // Remove from aboveOBs so we don't pick it again on next iteration
                    aboveOBs.remove(closestIdx)

        array<orderBlock> closestBelowOBs = array.new<orderBlock>()
        int belowCount = belowOBs.size() > 0 and outsideOBMax > 0 ? math.min(belowOBs.size(), outsideOBMax) : 0
        if belowCount > 0
            for i = 1 to belowCount
                orderBlock closest = na
                int closestIdx = -1
                for j = 0 to belowOBs.size() - 1
                    orderBlock candidate = belowOBs.get(j)
                    if closestIdx == -1
                        closest := candidate
                        closestIdx := j
                    else if candidate.barHigh > closest.barHigh
                        closest := candidate
                        closestIdx := j
                if closestIdx != -1
                    closestBelowOBs.push(closest)
                    // Remove from belowOBs so we don't pick it again
                    belowOBs.remove(closestIdx)

        // Combine: below | inRange | above  (use all in-range, and the top N closest)
        array<orderBlock> visible = array.new<orderBlock>()
        for ob in closestBelowOBs
            visible.push(ob)
        for ob in inRange
            visible.push(ob)
        for ob in closestAboveOBs
            visible.push(ob)

        int visibleCount = visible.size()

        // ── Dynamically Adjust Boxes & Labels Array Size ──
        int currentBoxCount = boxes.size()
        
        // Remove excess boxes
        if currentBoxCount > visibleCount
            for i = currentBoxCount - 1 to visibleCount
                box.delete(boxes.pop())
                label.delete(labels.pop())
        // Add needed boxes
        else if currentBoxCount < visibleCount
            for i = currentBoxCount to visibleCount - 1
                boxes.push(box.new(na, na, na, na, xloc = xloc.bar_time))
                labels.push(label.new(na, na, text = "", xloc = xloc.bar_time,
                     color = color(na), style = label.style_label_left,
                     textcolor = color.gray, size = size.tiny))

        // Iterate and render everything dynamically matched 1:1 with visible OBs
        for [idx, ob] in visible
            // Partially mitigated OBs turn grey; active OBs keep their bias colour
            color c = ob.partial
                 ? color.new(color.gray, 88)   // light grey = touched but not broken
                 : obType == 1
                      ? (ob.bias == BEARISH ? intBearOBColor  : intBullOBColor)
                      : (ob.bias == BEARISH ? swingBearOBColor : swingBullOBColor)

            // ── Box ──────────────────────────────────────────────────────────
            box b = boxes.get(idx)
            b.set_top_left_point(     chart.point.new(ob.barTime, na, ob.barHigh))
            b.set_bottom_right_point( chart.point.new(ob_rightTime, na, ob.barLow))
            b.set_border_color(obType == 1 ? na : c)
            b.set_bgcolor(c)

            // ── Label: vertically centered on the right inside the OB box ───────────────────────────
            string ob_tag = ob.isRefined ? ob.refinedTag : tf_tag
            // Position Y at the exact middle of the box
            float ob_midY = (ob.barHigh + ob.barLow) / 2
            label lbl = labels.get(idx)
            lbl.set_xy(ob_rightTime, ob_midY)       // anchor = right edge, vertically centered
            lbl.set_text(ob_tag)
            lbl.set_style(label.style_label_right)  // body is LEFT of anchor → inside box
            lbl.set_textcolor(color.new(ob.bias == BULLISH ? color.blue : color.red, 30))
            lbl.set_size(size.small)

//=============================================================================
// VALID OB DETECTION — Liquidity Sweep + Fair Value Gap (NEW LOGIC)
//=============================================================================
// A valid Order Block must satisfy ALL of the following in a 3-candle sequence:
//
//   bar[2]  = OB candle  → must TAKE LIQUIDITY of the previous candle
//             Bullish OB: bar[2].low  < bar[3].low   (swept previous low)
//             Bearish OB: bar[2].high > bar[3].high  (swept previous high)
//
//   bar[1]  = reaction candle (just needs to exist between OB and FVG bar)
//
//   bar[0]  = FVG candle → must create a FAIR VALUE GAP with bar[2]
//             Bullish FVG: bar[0].low  > bar[2].high  (gap above OB high)
//             Bearish FVG: bar[0].high < bar[2].low   (gap below OB low)
//
//   Trend filter: Bullish OB only stored in BULLISH trend, Bearish in BEARISH.
//
//   The OB box is drawn around bar[2]'s high and low.
//=============================================================================

// ── Step 1: Liquidity sweep at bar[2] ───────────────────────────────────────
ob_bullSweep = low[2]  < low[3]   // OB candle swept previous candle's LOW
ob_bearSweep = high[2] > high[3]  // OB candle swept previous candle's HIGH

// ── Step 2: FVG between bar[2] (OB candle) and bar[0] (current candle) ─────
//   Bullish: gap exists when current LOW is above OB candle's HIGH
ob_bullFVG  = low  > high[2]
//   Bearish: gap exists when current HIGH is below OB candle's LOW
ob_bearFVG  = high < low[2]

// ── Step 3: Both conditions met + optionally aligned with current swing trend ───────────
validBullOB = ob_bullSweep and ob_bullFVG and (not obTrendFilterInput or swingTrend.bias == BULLISH)
validBearOB = ob_bearSweep and ob_bearFVG and (not obTrendFilterInput or swingTrend.bias == BEARISH)

// ── Step 4: Store the OB (coordinates taken from bar[2]) ────────────────────
autoLtfStr = getAutoLTF()
hasAutoLtf = autoLtfStr != ""

calcLTF_OB_Data(int size) =>
    int tBias = calcTrendForSecurity(size)
    bool bullSweep = low[2] < low[3]
    bool bearSweep = high[2] > high[3]
    bool bullFVG = low > high[2]
    bool bearFVG = high < low[2]
    bool vBull = bullSweep and bullFVG and (not obTrendFilterInput or tBias == BULLISH)
    bool vBear = bearSweep and bearFVG and (not obTrendFilterInput or tBias == BEARISH)
    
    var float lastBull_H = na
    var float lastBull_L = na
    var int   lastBull_T = na
    var float lastBear_H = na
    var float lastBear_L = na
    var int   lastBear_T = na

    if vBull
        lastBull_H := high[2]
        lastBull_L := low[2]
        lastBull_T := time[2]
    if vBear
        lastBear_H := high[2]
        lastBear_L := low[2]
        lastBear_T := time[2]
        
    [lastBull_H, lastBull_L, lastBull_T, lastBear_H, lastBear_L, lastBear_T]

[ltfBull_H, ltfBull_L, ltfBull_T, ltfBear_H, ltfBear_L, ltfBear_T] = request.security(syminfo.tickerid, hasAutoLtf ? autoLtfStr : timeframe.period, calcLTF_OB_Data(swingsLengthInput), lookahead = barmerge.lookahead_off)

if hasAutoLtf and showRefinedOBInput
    if not na(ltfBull_T)
        bool exists = false
        if refinedOBs.size() > 0
            if refinedOBs.get(0).barTime == ltfBull_T and refinedOBs.get(0).bias == BULLISH
                exists := true
        if not exists
            refinedOBs.unshift(orderBlock.new(ltfBull_H, ltfBull_L, ltfBull_T, BULLISH))
            if refinedOBs.size() >= 100
                refinedOBs.pop()
                
    if not na(ltfBear_T)
        bool exists = false
        if refinedOBs.size() > 0
            if refinedOBs.get(0).barTime == ltfBear_T and refinedOBs.get(0).bias == BEARISH
                exists := true
        if not exists
            refinedOBs.unshift(orderBlock.new(ltfBear_H, ltfBear_L, ltfBear_T, BEARISH))
            if refinedOBs.size() >= 100
                refinedOBs.pop()

string tf_tag = formatTF(timeframe.period)

float bullH = high[2]
float bullL = low[2]
int bullT = time[2]
bool bullRefined = false
string bullTag = tf_tag

if validBullOB and hasAutoLtf and showRefinedOBInput
    for ref in refinedOBs
        if ref.bias == BULLISH and ref.barHigh <= bullH and ref.barLow >= bullL and ref.barTime >= bullT
            bullH := ref.barHigh
            bullL := ref.barLow
            bullT := ref.barTime
            bullRefined := true
            bullTag := tf_tag + "+" + formatTF(autoLtfStr)
            break

if validBullOB and showSwingOBInput
    ob_entry = orderBlock.new(bullH, bullL, bullT, BULLISH)
    ob_entry.isRefined := bullRefined
    ob_entry.refinedTag := bullTag
    if swingOBs.size() >= 100
        swingOBs.pop()
    swingOBs.unshift(ob_entry)


float bearH = high[2]
float bearL = low[2]
int bearT = time[2]
bool bearRefined = false
string bearTag = tf_tag

if validBearOB and hasAutoLtf and showRefinedOBInput
    for ref in refinedOBs
        if ref.bias == BEARISH and ref.barHigh <= bearH and ref.barLow >= bearL and ref.barTime >= bearT
            bearH := ref.barHigh
            bearL := ref.barLow
            bearT := ref.barTime
            bearRefined := true
            bearTag := tf_tag + "+" + formatTF(autoLtfStr)
            break
            
if validBearOB and showSwingOBInput
    ob_entry = orderBlock.new(bearH, bearL, bearT, BEARISH)
    ob_entry.isRefined := bearRefined
    ob_entry.refinedTag := bearTag
    if swingOBs.size() >= 100
        swingOBs.pop()
    swingOBs.unshift(ob_entry)

// ---- Delete mitigated OBs every bar ----
if showSwingOBInput
    deleteOBs(0)

if showInternalOBInput
    deleteOBs(1)

// ---- Draw on last confirmed / realtime bar ----
if barstate.islastconfirmedhistory or barstate.islast
    if showSwingOBInput
        drawOBs(0)
    if showInternalOBInput
        drawOBs(1)