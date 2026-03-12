import React, { useEffect, useRef } from 'react';
import {
  createChart,
  ColorType,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type Time,
  CandlestickSeries,
  LineSeries,
  createSeriesMarkers
} from 'lightweight-charts';
import { OrderBlockSeries } from '../plugins/OrderBlockSeries';
import { StructureSeries } from '../plugins/StructureSeries';

interface StructureData {
  time: number;
  level: number;
  kind: string;
  direction: string;
}

interface TrailsData {
  top: number | null;
  top_time: number | null;
  bottom: number | null;
  bottom_time: number | null;
}

interface ChartProps {
  data: CandlestickData<Time>[];
  obs: any[];
  structure: StructureData[];
  trend: string;
  trails: TrailsData;
  settings: {
    showFull: boolean;
    showPartial: boolean;
  };
}

const Chart: React.FC<ChartProps> = ({ data, obs, structure, trend, trails, settings }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick", Time> | null>(null);
  const markersPluginRef = useRef<any>(null);
  const obSeriesRef = useRef<any>(null);
  const structureLinesRef = useRef<any>(null);
  const trailTopSeriesRef = useRef<ISeriesApi<"Line", Time> | null>(null);
  const trailBottomSeriesRef = useRef<ISeriesApi<"Line", Time> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#fcfcf8' }, // Off-white cream background
        textColor: '#131722',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(19, 23, 34, 0.05)' },
        horzLines: { color: 'rgba(19, 23, 34, 0.05)' },
      },
      rightPriceScale: {
        borderColor: '#e0e3eb',
        scaleMargins: {
          top: 0.1,
          bottom: 0.1,
        },
      },
      timeScale: {
        borderColor: '#e0e3eb',
        timeVisible: true,
      },
      crosshair: {
        mode: 0,
        vertLine: { color: '#758696', width: 1 as any, style: 2 },
        horzLine: { color: '#758696', width: 1 as any, style: 2 },
      },
    });

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: '#ffffff',
      downColor: '#131722',
      borderUpColor: '#131722',
      borderDownColor: '#131722',
      wickUpColor: '#131722',
      wickDownColor: '#131722',
    });

    // Add Markers Plugin (Still useful for arrows/pivots if needed)
    const markersPlugin = createSeriesMarkers(candlestickSeries);

    // Add Custom OB Series
    const obSeries = chart.addCustomSeries(new OrderBlockSeries(), {
      priceLineVisible: false,
      lastValueVisible: false,
    });

    // Add Custom Structure Series (BOS/CHoCH lines)
    const structureLines = chart.addCustomSeries(new StructureSeries(), {
      priceLineVisible: false,
      lastValueVisible: false,
    });

    const trailTopSeries = chart.addSeries(LineSeries, {
      color: '#ef5350',
      lineWidth: 1,
      lineStyle: 0,
      priceLineVisible: false,
      lastValueVisible: false,
      title: 'Strong High',
    });

    const trailBottomSeries = chart.addSeries(LineSeries, {
      color: '#2962ff',
      lineWidth: 1,
      lineStyle: 0,
      priceLineVisible: false,
      lastValueVisible: false,
      title: 'Strong Low',
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    markersPluginRef.current = markersPlugin;
    obSeriesRef.current = obSeries;
    structureLinesRef.current = structureLines;
    trailTopSeriesRef.current = trailTopSeries;
    trailBottomSeriesRef.current = trailBottomSeries;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight
        });
      }
    };

    window.addEventListener('resize', handleResize);
    handleResize();

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Update Data & HUD/Structure
  useEffect(() => {
    if (candlestickSeriesRef.current && data.length > 0) {
      candlestickSeriesRef.current.setData(data);

      // 1. Structure Lines (BOS/CHoCH) via Custom Series
      if (structureLinesRef.current) {
        const structurePoints = data.map(candle => {
          const t = candle.time as number;
          const matches = structure.filter(s => s.time === t);

          if (matches.length === 0) return null;

          return {
            time: t as Time,
            lines: matches.map(s => ({
              level: s.level,
              label: s.kind,
              color: s.direction === 'bullish' ? '#2962ff' : '#ef5350',
              style: s.kind === 'CHoCH' ? 2 : 0 // Dashed for CHoCH
            }))
          };
        }).filter(Boolean) as any[];

        structureLinesRef.current.setData(structurePoints);
      }

      // 2. Strong/Weak Labels and Structure Markers
      if (markersPluginRef.current) {
        // Markers for structural breaks (arrows)
        const breakMarkers = structure.map(s => ({
          time: s.time as Time,
          position: s.direction === 'bullish' ? 'belowBar' : 'aboveBar' as any,
          color: s.direction === 'bullish' ? '#2962ff' : '#ef5350',
          shape: s.direction === 'bullish' ? 'arrowUp' : 'arrowDown' as any,
          text: s.kind,
          size: 0.8,
        }));

        // Trailing Extreme Labels (Strong/Weak)
        const trailMarkers: any[] = [];
        if (trails.top && trails.top_time) {
          trailMarkers.push({
            time: trails.top_time as Time,
            position: 'aboveBar',
            color: '#ef5350',
            shape: 'circle',
            text: trend === 'bearish' ? 'Strong High' : 'Weak High',
            size: 0.5
          });
        }
        if (trails.bottom && trails.bottom_time) {
          trailMarkers.push({
            time: trails.bottom_time as Time,
            position: 'belowBar',
            color: '#2962ff',
            shape: 'circle',
            text: trend === 'bullish' ? 'Strong Low' : 'Weak Low',
            size: 0.5
          });
        }

        markersPluginRef.current.setMarkers([...breakMarkers, ...trailMarkers]);
      }
    }
  }, [data, structure, trails, trend]);

  // Update OBs
  useEffect(() => {
    if (obSeriesRef.current && data.length > 0) {
      // Map OBs as segments for every bar they are active
      const formattedOBs = data.map(candle => {
        const t = candle.time as number;
        const segments = obs
          .filter(ob => t >= ob.time)
          .filter(ob => {
            // Filter based on settings and mitigation status
            if (ob.mitigated && !settings.showFull) return false;
            if (ob.partial && !ob.mitigated && !settings.showPartial) return false;
            return true;
          })
          .map(ob => {
            // Standard TradingView-style colors
            const bullFill = 'rgba(41, 98, 255, 0.12)';
            const bearFill = 'rgba(239, 83, 80, 0.12)';
            const bullBorder = 'rgba(41, 98, 255, 0.7)';
            const bearBorder = 'rgba(239, 83, 80, 0.7)';

            let color = ob.bias === 'bullish' ? bullFill : bearFill;
            let borderColor = 'transparent';

            if (ob.mitigated) {
              color = 'rgba(128, 128, 128, 0.08)';
              borderColor = 'rgba(128, 128, 128, 0.2)';
            } else if (ob.is_refined) {
              // Refined/Nested highlight: darker solid border
              borderColor = ob.bias === 'bullish' ? bullBorder : bearBorder;
            } else {
              // Standard active OB border (very subtle)
              borderColor = ob.bias === 'bullish' ? 'rgba(41, 98, 255, 0.3)' : 'rgba(239, 83, 80, 0.3)';
            }

            return {
              high: ob.cur_h,
              low: ob.cur_l,
              color,
              borderColor,
              is_refined: ob.is_refined
            };
          });

        return {
          time: t as Time,
          segments: segments
        };
      }).filter(d => d.segments.length > 0);

      obSeriesRef.current.setData(formattedOBs);
    }
  }, [obs, data, settings]);

  // Update Trails
  useEffect(() => {
    if (trailTopSeriesRef.current && trailBottomSeriesRef.current && data.length > 0) {
      const lastCandle = data[data.length - 1];
      const lastTime = lastCandle.time as number;

      if (trails.top && trails.top_time) {
        const pivotTime = trails.top_time as number;
        // Ensure strictly increasing times for LineSeries points
        const t2 = lastTime;
        const t1 = pivotTime === t2 ? t2 - 1 : pivotTime;

        if (t1 <= t2) {
          trailTopSeriesRef.current.setData([
            { time: t1 as Time, value: trails.top },
            { time: t2 as Time, value: trails.top }
          ]);
        } else {
          trailTopSeriesRef.current.setData([{ time: t2 as Time, value: trails.top }]);
        }

        trailTopSeriesRef.current.applyOptions({
          color: trend === 'bearish' ? '#ef5350' : 'rgba(239, 83, 80, 0.5)',
          lineStyle: trend === 'bearish' ? 0 : 2
        });
      } else {
        trailTopSeriesRef.current.setData([]);
      }

      if (trails.bottom && trails.bottom_time) {
        const pivotTime = trails.bottom_time as number;
        const t2 = lastTime;
        const t1 = pivotTime === t2 ? t2 - 1 : pivotTime;

        if (t1 <= t2) {
          trailBottomSeriesRef.current.setData([
            { time: t1 as Time, value: trails.bottom },
            { time: t2 as Time, value: trails.bottom }
          ]);
        } else {
          trailBottomSeriesRef.current.setData([{ time: t2 as Time, value: trails.bottom }]);
        }

        trailBottomSeriesRef.current.applyOptions({
          color: trend === 'bullish' ? '#2962ff' : 'rgba(41, 98, 255, 0.5)',
          lineStyle: trend === 'bullish' ? 0 : 2
        });
      } else {
        trailBottomSeriesRef.current.setData([]);
      }
    }
  }, [trails, data, trend]);

  return (
    <div className="flex-1 relative bg-[#fcfcf8]">
      <div ref={chartContainerRef} className="absolute inset-0" />

      {/* HUD Info */}
      <div className="absolute top-3 left-3 z-10 pointer-events-none flex gap-4 text-[11px] font-bold">
        <div className="flex gap-1.5 items-center bg-white/80 px-2 py-1 rounded border border-tv-border shadow-sm">
          <span className="text-tv-muted uppercase font-semibold">Trend</span>
          <span className={trend === 'bullish' ? 'text-tv-green' : trend === 'bearish' ? 'text-tv-red' : 'text-tv-muted'}>
            {trend === 'bullish' ? '▲ BULLISH' : trend === 'bearish' ? '▼ BEARISH' : '— NEUTRAL'}
          </span>
        </div>
        <div className="flex gap-1.5 items-center bg-white/80 px-2 py-1 rounded border border-tv-border shadow-sm">
          <span className="text-tv-muted uppercase font-semibold">OBs</span>
          <span className="text-tv-text font-bold uppercase">{obs.length}</span>
        </div>
        <div className="flex gap-1.5 items-center bg-white/80 px-2 py-1 rounded border border-tv-border shadow-sm">
          <span className="text-tv-muted uppercase font-semibold">Bars</span>
          <span className="text-tv-text font-bold uppercase">{data.length}</span>
        </div>
      </div>
    </div>
  );
};

export default Chart;
