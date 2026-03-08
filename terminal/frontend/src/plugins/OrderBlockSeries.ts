import { 
    type ICustomSeriesPaneView, 
    type ICustomSeriesPaneRenderer, 
    type PaneRendererCustomData, 
    type PriceToCoordinateConverter,
    type CustomData,
    type Time,
    type CustomSeriesWhitespaceData,
    type CustomSeriesOptions,
    customSeriesDefaultOptions
} from 'lightweight-charts';
import { type CanvasRenderingTarget2D } from 'fancy-canvas';

interface OBSegment {
    high: number;
    low: number;
    color: string;
    borderColor: string;
}

interface OBPoint extends CustomData<Time> {
    segments: OBSegment[];
}

class OrderBlockRenderer implements ICustomSeriesPaneRenderer {
    _data: PaneRendererCustomData<Time, OBPoint> | null = null;

    draw(target: CanvasRenderingTarget2D, priceConverter: PriceToCoordinateConverter): void {
        if (!this._data || this._data.bars.length === 0) return;

        target.useBitmapCoordinateSpace((scope) => {
            const ctx = scope.context;
            const horizontalPixelRatio = scope.horizontalPixelRatio;
            const verticalPixelRatio = scope.verticalPixelRatio;

            // Calculate bar width in pixels
            let barWidth = 6 * horizontalPixelRatio;
            if (this._data!.bars.length > 1) {
                barWidth = (this._data!.bars[1].x - this._data!.bars[0].x) * horizontalPixelRatio;
            }

            for (const bar of this._data!.bars) {
                if (!bar.originalData || !bar.originalData.segments) continue;
                
                const x = bar.x * horizontalPixelRatio;
                for (const seg of bar.originalData.segments) {
                    const yHigh = (priceConverter(seg.high) ?? 0) * verticalPixelRatio;
                    const yLow = (priceConverter(seg.low) ?? 0) * verticalPixelRatio;
                    
                    const height = Math.abs(yLow - yHigh);
                    ctx.fillStyle = seg.color;
                    ctx.fillRect(x, Math.min(yHigh, yLow), barWidth, height);

                    ctx.strokeStyle = seg.borderColor;
                    ctx.lineWidth = 1 * verticalPixelRatio;
                    ctx.beginPath();
                    ctx.moveTo(x, yHigh);
                    ctx.lineTo(x + barWidth, yHigh);
                    ctx.moveTo(x, yLow);
                    ctx.lineTo(x + barWidth, yLow);
                    ctx.stroke();
                }
            }
        });
    }

    update(data: PaneRendererCustomData<Time, OBPoint>): void {
        this._data = data;
    }
}

export class OrderBlockSeries implements ICustomSeriesPaneView<Time, OBPoint> {
    _renderer: OrderBlockRenderer = new OrderBlockRenderer();

    priceValueBuilder(plotRow: OBPoint): number[] {
        if (plotRow.segments && plotRow.segments.length > 0) {
            const highs = plotRow.segments.map(s => s.high);
            const lows = plotRow.segments.map(s => s.low);
            return [Math.max(...highs), Math.min(...lows)];
        }
        return [];
    }

    isWhitespace(data: OBPoint | CustomSeriesWhitespaceData<Time>): data is CustomSeriesWhitespaceData<Time> {
        const d = data as OBPoint;
        return !d.segments || d.segments.length === 0;
    }

    renderer(): ICustomSeriesPaneRenderer {
        return this._renderer;
    }

    update(data: PaneRendererCustomData<Time, OBPoint>): void {
        this._renderer.update(data);
    }

    defaultOptions(): CustomSeriesOptions {
        return {
            ...customSeriesDefaultOptions,
            color: '#2962ff',
        };
    }
}
