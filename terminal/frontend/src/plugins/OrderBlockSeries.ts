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
    is_refined: boolean;
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
                    const top = Math.min(yHigh, yLow);

                    // Draw fill
                    ctx.fillStyle = seg.color;
                    ctx.fillRect(x, top, barWidth, height);

                    // Draw borders
                    ctx.strokeStyle = seg.borderColor;
                    ctx.lineWidth = 1 * verticalPixelRatio;
                    ctx.beginPath();
                    ctx.moveTo(x, yHigh);
                    ctx.lineTo(x + barWidth, yHigh);
                    ctx.moveTo(x, yLow);
                    ctx.lineTo(x + barWidth, yLow);
                    ctx.stroke();

                    // Draw Text Label (only on the starting bar of the OB or if wide enough)
                    // For simplicity, we just draw it if the segment exists. 
                    // To prevent overlap, we check a flag or just draw it once per unique OB time if we had that info.
                    // Here we'll draw it on every bar but centered or left-aligned.
                    ctx.fillStyle = seg.borderColor; // Use border color for text
                    ctx.font = `${Math.floor(8 * verticalPixelRatio)}px Arial`;
                    ctx.textAlign = 'left';
                    ctx.textBaseline = 'middle';

                    const label = seg.is_refined ? 'Refined OB' : 'OB';
                    const textX = x + 2 * horizontalPixelRatio;
                    const textY = top + height / 2;

                    // Only draw text if it fits vertically
                    if (height > 10 * verticalPixelRatio) {
                        ctx.fillText(label, textX, textY);
                    }
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
