export const API = location.origin;
export const state = {
  lat: Number(localStorage.getItem('wg_lat') || 28.6139),
  lon: Number(localStorage.getItem('wg_lon') || 77.2090),
  city: localStorage.getItem('wg_city') || 'New Delhi'
};
export function setLocation(city, lat, lon){
  state.city=city; state.lat=Number(lat); state.lon=Number(lon);
  localStorage.setItem('wg_city',city); localStorage.setItem('wg_lat',lat); localStorage.setItem('wg_lon',lon);
}
export async function api(path, options={}){
  const token = localStorage.getItem('wg_token');
  const headers = {...(options.headers||{})};
  if(options.body && !headers['Content-Type']) headers['Content-Type']='application/json';
  if(token) headers.Authorization=`Bearer ${token}`;
  const res = await fetch(`${API}${path}`, {...options, headers});
  const data = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}
export function number(v, suffix=''){ return v===undefined || v===null ? '—' : `${v}${suffix}`; }
export function setupNav(){
  document.querySelectorAll('[data-current-city]').forEach(el=>el.textContent=state.city);
  document.querySelectorAll('[data-use-location]').forEach(btn=>btn.addEventListener('click',()=>{
    if(!navigator.geolocation) return alert('Geolocation not supported');
    navigator.geolocation.getCurrentPosition(p=>{setLocation('My location',p.coords.latitude,p.coords.longitude); location.reload();},()=>alert('Location permission was not granted.'));
  }));
  const user=JSON.parse(localStorage.getItem('wg_user')||'null');
  document.querySelectorAll('[data-user-name]').forEach(el=>el.textContent=user?.name||'Guest');
}
export async function citySelector(select){
  const cities = await api('/api/cities');
  select.innerHTML = cities.map(c=>`<option value="${c.lat},${c.lon}" ${c.name===state.city?'selected':''}>${c.name}</option>`).join('');
  select.addEventListener('change',()=>{const c=cities[select.selectedIndex];setLocation(c.name,c.lat,c.lon);location.reload();});
}
setupNav();
