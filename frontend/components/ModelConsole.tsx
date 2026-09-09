import { useEffect, useState } from 'react';
import { BrainCircuit, Play } from 'lucide-react';
import { useApp } from '@/lib/context';
import { api, type Row } from '@/lib/api';
import { Choice } from './WeatherUI';
export default function ModelConsole() {
  const { weather } = useApp();
  const [models, setModels] = useState<Row[]>([]),
    [kind, setKind] = useState('disaster'),
    [values, setValues] = useState<Record<string, string>>({}),
    [result, setResult] = useState<Row | null>(null),
    [error, setError] = useState(''),
    [busy, setBusy] = useState(false);
  useEffect(() => {
    api('/api/models/status')
      .then((d) => setModels(d.models))
      .catch((e) => setError(e.message));
  }, []);
  const model = models.find((m) => m.name === kind);
  const names: string[] = model?.expected_features || [
    'temperature_2m',
    'precipitation',
    'wind_gusts_10m',
  ];
  useEffect(() => {
    setValues(
      Object.fromEntries(
        names.map((name) => [
          name,
          weather?.current[name] == null ? '' : String(weather.current[name]),
        ]),
      ),
    );
    setResult(null);
  }, [kind, weather, model?.status]);
  return (
    <section className="card" style={{ marginTop: 20 }}>
      <div className="card-head">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <BrainCircuit size={19} />
          Prediction workbench
        </h2>
        <Choice
          label="Prediction model"
          value={kind}
          onChange={setKind}
          items={['weather', 'disaster']}
        />
      </div>
      <span className="badge neutral">
        {model?.status || 'CHECKING'} · {model?.mode || 'FALLBACK'}
      </span>
      <p className="muted" style={{ fontSize: 14, marginTop: 12 }}>
        {model?.status === 'loaded'
          ? 'Enter the exact training features. Values are ordered by the validated model schema.'
          : 'No trained model is loaded. Disaster screening uses explicit thresholds; weather prediction returns no synthetic estimate.'}
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          try {
            const features = Object.fromEntries(
              Object.entries(values)
                .filter(([, v]) => v !== '')
                .map(([k, v]) => [k, Number(v)]),
            );
            setResult(
              await api('/api/predict/' + kind, {
                method: 'POST',
                body: JSON.stringify({ features }),
              }),
            );
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <div className="detail-grid">
          {names.map((name) => (
            <label className="form-field" key={name}>
              {name.replaceAll('_', ' ')}
              <input
                type="number"
                step="any"
                required={model?.status === 'loaded'}
                value={values[name] || ''}
                onChange={(e) =>
                  setValues({ ...values, [name]: e.target.value })
                }
              />
            </label>
          ))}
        </div>
        <button className="button" disabled={busy}>
          <Play size={15} />
          {busy ? 'Evaluating…' : 'Evaluate supplied features'}
        </button>
      </form>
      {error && <p className="error-note">{error}</p>}
      {result && (
        <div className="alert-banner">
          <div>
            <h3>
              {result.event || result.message || String(result.prediction)}
            </h3>
            <p>
              {result.model_source} · {result.severity || result.mode}
              {result.confidence != null
                ? ` · Calibrated confidence ${(result.confidence * 100).toFixed(1)}%`
                : ''}
            </p>
            {result.recommendations?.map((r: string) => (
              <p key={r}>{r}</p>
            ))}
            {result.limitations && <p>{result.limitations}</p>}
          </div>
        </div>
      )}
    </section>
  );
}
