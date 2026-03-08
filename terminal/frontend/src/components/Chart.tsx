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

    // Add Markers Plugin
    const markersPlugin = createSeriesMarkers(candlestickSeries);

    // Add Custom OB Series
    const obSeries = chart.addCustomSeries(new OrderBlockSeries(), {
        priceLineVisible: false,
        lastValueVisible: false,
    });

    const trailTopSeries = chart.addSeries(LineSeries, {
        color: '#ef5350',
        lineWidth: 1,
        lineStyle: 0,
        priceLineVisible: false,
        lastValueVisible: false,
    });

    const trailBottomSeries = chart.addSeries(LineSeries, {
        color: '#2962ff',
        lineWidth: 1,
        lineStyle: 0,
        priceLineVisible: false,
        lastValueVisible: false,
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    markersPluginRef.current = markersPlugin;
    obSeriesRef.current = obSeries;
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

  // Update Data & Markers
  useEffect(() => {
    if (candlestickSeriesRef.current && data.length > 0) {
      candlestickSeriesRef.current.setData(data);

      // Add Markers for Structure via Plugin
      if (markersPluginRef.current) {
        const markers = structure
          .filter(s => s.time && s.level && s.kind)
          .map(s => ({
            time: s.time as Time,
            position: s.direction === 'bullish' ? 'belowBar' : 'aboveBar' as any,
            color: '#131722',
            shape: s.direction === 'bullish' ? 'arrowUp' : 'arrowDown' as any,
            text: s.kind,
            size: 0.8,
          }));
        markersPluginRef.current.setMarkers(markers);
      }
    }
  }, [data, structure]);

  // Update OBs
  useEffect(() => {
    if (obSeriesRef.current && data.length > 0) {
        // Map OBs as segments for every bar they are active
        const formattedOBs = data.map(candle => {
            const t = candle.time as number;
            const segments = obs
                .filter(ob => t >= ob.time)
                .filter(ob => {
                    if (ob.mitigated && !settings.showFull) return false;
                    if (ob.partial && !ob.mitigated && !settings.showPartial) return false;
                    return true;
                })
                .map(ob => {
                    const bullColor = 'rgba(41, 107, 255, 0.12)';
                    const bearColor = 'rgba(239, 83, 80, 0.12)';

                    let color = ob.bias === 'bullish' ? bullColor : bearColor;
                    let borderColor = 'transparent';
                    
                    if (ob.mitigated) {
                        color = 'rgba(128, 128, 128, 0.12)';
                        borderColor = 'rgba(128, 128, 128, 0.3)';
                    }

                    // Refined/Nested highlight: Prompt requested "darker border"
                    if (ob.is_refined && !ob.mitigated) {
                        borderColor = ob.bias === 'bullish' ? 'rgba(41, 107, 255, 0.95)' : 'rgba(239, 83, 80, 0.95)';
                        // Fill stays light but border becomes solid and dark
                    }

                    return {
                        high: ob.cur_h,
                        low: ob.cur_l,
                        color,
                        borderColor,
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
