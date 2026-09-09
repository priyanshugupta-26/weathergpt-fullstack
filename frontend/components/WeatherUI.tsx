import { useId } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  BarChart,
  Bar,
} from 'recharts';
import {
  CloudSun,
  Sun,
  Wind,
  Droplets,
  Gauge,
  MapPin,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { number, condition, type Row } from '@/lib/api';
import { useApp } from '@/lib/context';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
export function Choice({
  value,
  onChange,
  items,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  items: string[] | { value: string; label: string }[];
  label: string;
}) {
  return (
    <Select value={value} onValueChange={(v) => v && onChange(v)}>
      <SelectTrigger aria-label={label}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {items.map((i) =>
          typeof i === 'string' ? (
            <SelectItem key={i} value={i}>
              {i}
            </SelectItem>
          ) : (
            <SelectItem key={i.value} value={i.value}>
              {i.label}
            </SelectItem>
          ),
        )}
      </SelectContent>
    </Select>
  );
}
export function Heading({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}
export function Empty({
  title,
  children,
  retry,
}: {
  title: string;
  children?: React.ReactNode;
  retry?: () => void;
}) {
  return (
    <div className="empty-state">
      <h3>{title}</h3>
      <p>{children}</p>
      {retry && (
        <button className="button" onClick={retry}>
          <RefreshCw size={14} />
          Try again
        </button>
      )}
    </div>
  );
}
export function Freshness() {
  const { weather } = useApp();
  if (!weather) return null;
  return (
    <div className="freshness">
      {weather.source} ·{' '}
      {weather.status === 'live'
        ? 'Model-based conditions'
        : 'Data unavailable'}
      {weather.timestamp && (
        <>
          {' '}
          · {weather.timestamp.replace('T', ' ')} ({weather.timezone})
        </>
      )}
    </div>
  );
}
export function CurrentCard() {
  const { place, weather, loading, forecastSource, setForecastSource } = useApp(),
    c = weather?.current || {};
  return (
    <section className="card current-card">
      <div className="card-head" style={{ marginBottom: 0 }}>
        <div className="place-heading">
          <MapPin size={17} />
          {place.name}
        </div>
        <span
          className={`badge ${weather?.status === 'live' ? '' : 'neutral'}`}
        >
          <span className="dot" />
          {loading
            ? 'UPDATING'
            : weather?.status === 'live'
              ? 'LIVE'
              : 'UNAVAILABLE'}
        </span>
      </div>
      <div className="current-date">
        {new Date().toLocaleDateString('en', {
          weekday: 'long',
          day: 'numeric',
          month: 'long',
        })}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, margin: '10px 0 6px', flexWrap: 'wrap' }}>
        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase' }}>Source:</span>
        {[
          { id: 'AUTO', label: '✨ Auto' },
          { id: 'WEATHERGPT ML', label: '⚡ WeatherGPT ML' },
          { id: 'OPEN-METEO', label: '🌐 Open-Meteo' },
        ].map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => setForecastSource(s.id)}
            style={{
              fontSize: 11,
              fontWeight: 600,
              padding: '2px 9px',
              borderRadius: 12,
              cursor: 'pointer',
              border: forecastSource === s.id ? '1px solid #10b981' : '1px solid var(--line)',
              background: forecastSource === s.id
                ? (s.id === 'WEATHERGPT ML' ? 'rgba(16, 185, 129, 0.22)' : 'rgba(59, 130, 246, 0.22)')
                : 'transparent',
              color: forecastSource === s.id
                ? (s.id === 'WEATHERGPT ML' ? '#34d399' : '#60a5fa')
                : 'var(--muted)',
              transition: 'all 0.15s ease',
            }}
          >
            {s.label}
          </button>
        ))}
      </div>
      {loading && !weather ? (
        <Skeleton className="mt-8 h-24 w-40" />
      ) : (
        <div className="temperature">
          {number(c.temperature_2m)}
          <sup>°C</sup>
        </div>
      )}
      <CloudSun className="current-sky" size={85} strokeWidth={1} />
      <p className="condition">{condition(c.weather_code)}</p>
      <p className="feels">
        Feels like {number(c.apparent_temperature)}° · H:{' '}
        {number(weather?.daily[0]?.temperature_2m_max)}° L:{' '}
        {number(weather?.daily[0]?.temperature_2m_min)}°
      </p>
      <div className="weather-stats">
        {[
          [Wind, 'Wind', c.wind_speed_10m, 'km/h'],
          [Droplets, 'Humidity', c.relative_humidity_2m, '%'],
          [Gauge, 'Pressure', c.pressure_msl, 'hPa'],
        ].map(([Icon, label, value, unit]: any) => (
          <div key={label} className="weather-stat">
            <Icon />
            <strong>
              {number(value)} <small>{unit}</small>
            </strong>
            <small>{label}</small>
          </div>
        ))}
      </div>
      <Freshness />
    </section>
  );
}
export function Chart({
  data,
  field = 'temperature_2m',
  unit = '°C',
  bar = false,
  tall = false,
}: {
  data: Row[];
  field?: string;
  unit?: string;
  bar?: boolean;
  tall?: boolean;
}) {
  const id = useId().replace(/:/g, '');
  if (!data.some((d) => typeof d[field] === 'number'))
    return <div className="chart-empty">No data available for this range.</div>;
  const prepared = data.map((d) => ({
    ...d,
    label: d.time?.includes('T') ? d.time.slice(11, 16) : d.time?.slice(5),
  }));
  return (
    <div className={`chart ${tall ? 'chart-tall' : ''}`}>
      <ResponsiveContainer
        width="100%"
        height="100%"
        initialDimension={{ width: 400, height: tall ? 300 : 200 }}
      >
        {bar ? (
          <BarChart data={prepared}>
            <CartesianGrid
              stroke="var(--line)"
              vertical={false}
              strokeDasharray="3 5"
            />
            <XAxis
              dataKey="label"
              tick={{ fill: 'var(--muted)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              minTickGap={35}
            />
            <YAxis
              tick={{ fill: 'var(--muted)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              width={35}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--panel)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                color: 'var(--text)',
              }}
              formatter={(v: any) => [
                `${v} ${unit}`,
                field.replaceAll('_', ' '),
              ]}
            />
            <Bar dataKey={field} fill="#69c9d8" radius={[3, 3, 0, 0]} />
          </BarChart>
        ) : (
          <AreaChart
            data={prepared}
            margin={{ top: 10, right: 5, left: -12, bottom: 0 }}
          >
            <defs>
              <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#6bdbc9" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#6bdbc9" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid
              stroke="var(--line)"
              vertical={false}
              strokeDasharray="3 5"
            />
            <XAxis
              dataKey="label"
              tick={{ fill: 'var(--muted)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              minTickGap={35}
            />
            <YAxis
              tick={{ fill: 'var(--muted)', fontSize: 11 }}
              axisLine={false}
              tickLine={false}
              domain={['auto', 'auto']}
              unit={unit === '°C' ? '°' : ''}
            />
            <Tooltip
              contentStyle={{
                background: 'var(--panel)',
                border: '1px solid var(--line)',
                borderRadius: 8,
                color: 'var(--text)',
              }}
              formatter={(v: any) => [
                `${v} ${unit}`,
                field.replaceAll('_', ' '),
              ]}
            />
            <Area
              type="monotone"
              dataKey={field}
              stroke="#6bdbc9"
              strokeWidth={2.5}
              fill={`url(#${id})`}
              connectNulls={false}
              isAnimationActive={false}
            />
          </AreaChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
export function Metric({
  icon: Icon,
  label,
  value,
  unit,
}: {
  icon: any;
  label: string;
  value: unknown;
  unit: string;
}) {
  return (
    <div className="card metric">
      <span className="metric-icon">
        <Icon size={19} />
      </span>
      <div>
        <small>{label}</small>
        <strong>
          {typeof value === 'string'
            ? value
            : number(value, unit === 'mm' ? 1 : 0)}{' '}
          <span style={{ fontSize: 12, color: 'var(--muted)' }}>{unit}</span>
        </strong>
      </div>
    </div>
  );
}
export function Days() {
  const { weather } = useApp();
  return (
    <div className="days">
      {weather?.daily.map((d, i) => (
        <div className="card day" key={d.time}>
          <span style={{ fontSize: 13 }}>
            {i === 0
              ? 'Today'
              : new Date(d.time + 'T12:00:00').toLocaleDateString('en', {
                  weekday: 'short',
                })}
          </span>
          {d.weather_code < 3 ? <Sun size={26} /> : <CloudSun size={26} />}
          <span>
            {number(d.temperature_2m_max)}°{' '}
            <span className="muted">{number(d.temperature_2m_min)}°</span>
          </span>
          <small className="cyan">
            {number(d.precipitation_probability_max)}% rain
          </small>
        </div>
      ))}
    </div>
  );
}
