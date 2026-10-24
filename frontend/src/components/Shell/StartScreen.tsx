import { useUIStore } from "../../state/store";
import { EXAMPLES, HOW_IT_WORKS } from "../../constants";
import styles from "./StartScreen.module.css";

interface Props {
  onRun: (query: string) => void;
}

/** The start screen: question field, examples, and the 4-step "how it works" list. */
export function StartScreen({ onRun }: Props) {
  const question = useUIStore((s) => s.question);
  const setQuestion = useUIStore((s) => s.setQuestion);

  return (
    <div className={styles.start}>
      <label className={styles.label} htmlFor="question">
        What do you want to test?
      </label>
      <p className={styles.helper}>
        Describe a target, a compound class or a disease mechanism. Lab Planner checks how
        crowded the topic is, designs a first dose-response experiment for an Opentrons Flex
        robot, runs it in the Opentrons simulator, and estimates how much real-world noise
        will blur the answer.
      </p>

      <div className={styles.row}>
        <input
          id="question"
          className={styles.input}
          value={question}
          placeholder="HER2 kinase inhibitors in breast cancer"
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && question.trim()) onRun(question.trim());
          }}
        />
        <button
          className={styles.run}
          disabled={!question.trim()}
          onClick={() => onRun(question.trim())}
        >
          Run
        </button>
      </div>

      <h2 className={styles.tryLabel}>Try one</h2>
      <ul className={styles.examples}>
        {EXAMPLES.map((ex) => (
          <li key={ex}>
            <button className={styles.example} onClick={() => { setQuestion(ex); onRun(ex); }}>
              {ex}
            </button>
          </li>
        ))}
      </ul>

      <h2 className={styles.tryLabel}>How it works</h2>
      <ol className={styles.steps}>
        {HOW_IT_WORKS.map((s, i) => (
          <li key={i}>
            <span className={styles.stepNum}>{i + 1}</span> {s}
          </li>
        ))}
      </ol>
    </div>
  );
}
