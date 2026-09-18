export default function ProgressBar({ value }) {
  const percent = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <span className="progress-cell">
      <span className="progress-track">
        <span
          className={`progress-fill${percent >= 100 ? ' is-done' : ''}`}
          style={{ width: `${percent}%` }}
        />
      </span>
      {percent}%
    </span>
  );
}
