import * as Slider from "@radix-ui/react-slider";
import { Num } from "../Num/Num";
import { assumed, derived, src } from "../Num/provenance";
import { AXES, AXIS_LABEL, AXIS_MEANING, contribution, weightedTotal } from "../../lib/matrix";
import { useUIStore } from "../../state/store";
import { axisIsAssumed } from "../../api/normalize";
import type { AxisKey, TopicReport } from "../../api/types";
import styles from "./MatrixTable.module.css";

interface Props {
  topic: TopicReport;
}

/** Viability matrix with live weight sliders (BRIEF 5.6). The total recomputes in the
 *  browser; with default weights it equals the backend total within 1e-6. */
export function MatrixTable({ topic }: Props) {
  const weights = useUIStore((s) => s.weights);
  const setWeight = useUIStore((s) => s.setWeight);
  const resetWeights = useUIStore((s) => s.resetWeights);

  const unavailable = topic.matrix.unavailable_axes ?? [];
  const isUnavailable = (a: AxisKey) => unavailable.includes(a);
  const axes = Object.fromEntries(AXES.map((a) => [a, topic.matrix[a]])) as Record<AxisKey, number>;
  const total = weightedTotal(axes, weights, unavailable);
  const availableAxes = AXES.filter((a) => !isUnavailable(a));
  const weightSum = availableAxes.reduce((s, k) => s + weights[k], 0);

  return (
    <div className={styles.wrap}>
      <h3 className={styles.title}>How viable is this topic?</h3>
      <table className={styles.table}>
        <tbody>
          {AXES.map((axis) => {
            const value = axes[axis];
            const unavailableAxis = isUnavailable(axis);
            const share = weightSum > 0 ? weights[axis] / weightSum : 0;
            const contrib = contribution(axis, axes, weights, unavailable);
            const srcForAxis = topic.matrix.axis_sources?.[axis];
            const prov = srcForAxis
              ? src(srcForAxis, topic.matrix.axis_notes?.[axis])
              : assumed("Assumed value. Not computed from this topic's data.");
            if (unavailableAxis) {
              return (
                <tr key={axis} className={styles.unavailable}>
                  <th className={styles.axis}>
                    {AXIS_LABEL[axis]}
                    <span className={styles.meaning}>{AXIS_MEANING[axis]}</span>
                  </th>
                  <td className={styles.valCell} colSpan={3}>
                    <span className={styles.unavailableNote}>Unavailable offline</span>
                  </td>
                </tr>
              );
            }
            return (
              <tr key={axis} className={axisIsAssumed(topic, axis) ? styles.assumed : ""}>
                <th className={styles.axis}>
                  {AXIS_LABEL[axis]}
                  <span className={styles.meaning}>{AXIS_MEANING[axis]}</span>
                </th>
                <td className={styles.valCell}>
                  <div className={styles.bar}>
                    <div className={styles.fill} style={{ width: `${value * 100}%` }} />
                  </div>
                  <Num value={value.toFixed(2)} provenance={prov} className={styles.val} />
                </td>
                <td className={styles.sliderCell}>
                  <Slider.Root
                    className={styles.slider}
                    value={[weights[axis] * 100]}
                    min={0} max={100} step={5}
                    onValueChange={([v]) => setWeight(axis, v / 100)}
                    aria-label={`${AXIS_LABEL[axis]} weight`}
                  >
                    <Slider.Track className={styles.track}>
                      <Slider.Range className={styles.range} />
                    </Slider.Track>
                    <Slider.Thumb className={styles.thumb} />
                  </Slider.Root>
                  <span className={styles.shareLabel}>{Math.round(share * 100)}%</span>
                </td>
                <td className={styles.contrib}>{contrib.toFixed(2)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className={styles.totalRow}>
        <span className={styles.totalLabel}>Viability</span>
        <Num
          value={weightSum > 0 ? total.toFixed(2) : "No weights set"}
          className={styles.total}
          provenance={derived(
            "Weighted mean of the available axes: sum(axis x weight) / sum(weight).",
            availableAxes.map((a) => ({ label: AXIS_LABEL[a], source: topic.matrix.axis_sources?.[a] })),
          )}
        />
        <button className={styles.reset} onClick={resetWeights}>Reset weights</button>
      </div>
      {unavailable.length > 0 && (
        <p className={styles.axesNote}>
          Viability over {availableAxes.length} of {AXES.length} axes. {unavailable.length === 1 ? "One axis is" : `${unavailable.length} axes are`} unavailable offline.
        </p>
      )}
    </div>
  );
}
