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

interface StructureLine {
    level: number;
    label: string;
    color: string;
    style: number; // 0: solid, 2: dashed
}

interface StructurePoint extends CustomData<Time> {
    lines: StructureLine[];
}

class StructureRenderer implements ICustomSeriesPaneRenderer {
    _data: PaneRendererCustomData<Time, StructurePoint> | null = null;

    draw(target: CanvasRenderingTarget2D, priceConverter: PriceToCoordinateConverter): void {
        if (!this._data || this._data.bars.length === 0) return;

        target.useBitmapCoordinateSpace((scope) => {
            const ctx = scope.context;
            const horizontalPixelRatio = scope.horizontalPixelRatio;
            const verticalPixelRatio = scope.verticalPixelRatio;

            let barWidth = 6 * horizontalPixelRatio;
            if (this._data!.bars.length > 1) {
                barWidth = (this._data!.bars[1].x - this._data!.bars[0].x) * horizontalPixelRatio;
            }

            for (const bar of this._data!.bars) {
                if (!bar.originalData || !bar.originalData.lines) continue;

                const x = bar.x * horizontalPixelRatio;
                for (const line of bar.originalData.lines) {
                    const y = (priceConverter(line.level) ?? 0) * verticalPixelRatio;

                    ctx.strokeStyle = line.color;
                    ctx.lineWidth = 1 * verticalPixelRatio;
                    if (line.style === 2) {
                        ctx.setLineDash([4 * horizontalPixelRatio, 4 * horizontalPixelRatio]);
                    } else {
                        ctx.setLineDash([]);
                    }

                    ctx.beginPath();
                    ctx.moveTo(x, y);
                    ctx.lineTo(x + barWidth, y);
                    ctx.stroke();

                    // Reset dash for text
                    ctx.setLineDash([]);

                    // Draw Label
                    ctx.fillStyle = line.color;
                    ctx.font = `bold ${Math.floor(9 * verticalPixelRatio)}px Arial`;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(line.label, x + barWidth / 2, y - 2 * verticalPixelRatio);
                }
            }
        });
    }

    update(data: PaneRendererCustomData<Time, StructurePoint>): void {
        this._data = data;
    }
}

export class StructureSeries implements ICustomSeriesPaneView<Time, StructurePoint> {
    _renderer: StructureRenderer = new StructureRenderer();

    priceValueBuilder(plotRow: StructurePoint): number[] {
        if (plotRow.lines && plotRow.lines.length > 0) {
            return plotRow.lines.map(l => l.level);
        }
        return [];
    }

    isWhitespace(data: StructurePoint | CustomSeriesWhitespaceData<Time>): data is CustomSeriesWhitespaceData<Time> {
        const d = data as StructurePoint;
        return !d.lines || d.lines.length === 0;
    }

    renderer(): ICustomSeriesPaneRenderer {
        return this._renderer;
    }

    update(data: PaneRendererCustomData<Time, StructurePoint>): void {
        this._renderer.update(data);
    }

    defaultOptions(): CustomSeriesOptions {
        return {
            ...customSeriesDefaultOptions,
        };
    }
}
