import { useEffect, useState } from 'react';
import { api, type Place } from '@/lib/api';
import { useApp } from '@/lib/context';
import {
  Combobox,
  ComboboxInput,
  ComboboxContent,
  ComboboxList,
  ComboboxItem,
  ComboboxEmpty,
} from '@/components/ui/combobox';
export default function Search() {
  const { setPlace, toast } = useApp();
  const [query, setQuery] = useState(''),
    [items, setItems] = useState<Place[]>([]),
    [loading, setLoading] = useState(false),
    [status, setStatus] = useState('Type a city or coordinates');
  useEffect(() => {
    if (query.length < 2) {
      setItems([]);
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => {
      setLoading(true);
      api(`/api/locations/search?q=${encodeURIComponent(query)}`, {
        signal: controller.signal,
      })
        .then((d) => {
          setItems(d.results);
          setStatus(d.message || 'No locations found');
        })
        .catch((e) => {
          if (e.name !== 'AbortError') setStatus(e.message);
        })
        .finally(() => setLoading(false));
    }, 400);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);
  return (
    <div className="search-area">
      <Combobox
        items={items}
        filter={null}
        itemToStringLabel={(p: Place) =>
          p ? `${p.name}${p.country ? ', ' + p.country : ''}` : ''
        }
        onInputValueChange={setQuery}
        onValueChange={(p: Place | null) => {
          if (p) {
            setPlace(p);
            toast(`Weather context changed to ${p.name}`);
          }
        }}
      >
        <ComboboxInput
          aria-label="Search location"
          placeholder="Search city or coordinates…"
          showClear
          className="h-10 w-full bg-card"
        />
        <ComboboxContent>
          <ComboboxEmpty>{loading ? 'Searching…' : status}</ComboboxEmpty>
          <ComboboxList>
            {(p: Place) => (
              <ComboboxItem key={`${p.latitude}:${p.longitude}`} value={p}>
                <span>
                  {p.name}
                  <small style={{ display: 'block' }}>
                    {p.admin1} {p.country}
                  </small>
                </span>
              </ComboboxItem>
            )}
          </ComboboxList>
        </ComboboxContent>
      </Combobox>
    </div>
  );
}
