import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { Plus, Minus, RotateCcw } from 'lucide-react';
import type { Place, Row } from '@/lib/api';

export function xyz(lat: number, lon: number, r = 1) {
  const a = (lat * Math.PI) / 180,
    b = (lon * Math.PI) / 180;
  return new THREE.Vector3(
    r * Math.cos(a) * Math.cos(b),
    r * Math.sin(a),
    -r * Math.cos(a) * Math.sin(b),
  );
}
// Inverse-distance interpolation of real provider vectors on a sparse regional grid.
export function interpolate(cells: Row[], lat: number, lon: number) {
  const near = cells
    .map((c) => ({
      c,
      d:
        (c.latitude - lat) ** 2 +
        (((c.longitude - lon + 540) % 360) - 180) ** 2,
    }))
    .sort((a, b) => a.d - b.d)
    .slice(0, 4);
  if (!near.length || near[0].d > 25) return null;
  let u = 0,
    v = 0,
    w = 0;
  for (const p of near) {
    const weight = 1 / Math.max(0.001, p.d);
    u += p.c.u_component * weight;
    v += p.c.v_component * weight;
    w += weight;
  }
  return { u: u / w, v: v / w };
}
const fields: Record<string, string> = {
  Wind: 'wind_speed_10m',
  Rainfall: 'precipitation',
  Temperature: 'temperature_2m',
  Humidity: 'relative_humidity_2m',
  Pressure: 'pressure_msl',
  'Cloud Cover': 'cloud_cover',
};
const ranges: Record<string, [number, number]> = {
  Wind: [0, 60],
  Rainfall: [0, 20],
  Temperature: [-10, 45],
  Humidity: [0, 100],
  Pressure: [970, 1040],
  'Cloud Cover': [0, 100],
};
export default function Globe({
  place,
  onSelect,
  layer = 'Wind',
  cells = [],
  events = [],
  onEvent,
}: {
  place: Place;
  onSelect: (p: Place) => void;
  layer?: string;
  cells?: Row[];
  events?: Row[];
  onEvent?: (r: Row) => void;
}) {
  const host = useRef<HTMLDivElement>(null),
    actions = useRef<{ zoom: (n: number) => void; reset: () => void } | null>(
      null,
    ),
    latest = useRef({ place, onSelect, layer, cells, events, onEvent });
  const [error, setError] = useState('');
  latest.current = { place, onSelect, layer, cells, events, onEvent };
  useEffect(() => {
    if (!host.current) return;
    const el = host.current;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setError(
        'WebGL is unavailable on this device. Use search and the selected-location data below.',
      );
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
    camera.position.copy(xyz(place.latitude, place.longitude, 3.5));
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.enablePan = false;
    controls.minDistance = 1.6;
    controls.maxDistance = 6;
    controls.rotateSpeed = 0.55;
    const earth = new THREE.Mesh(
      new THREE.SphereGeometry(1, 96, 64),
      new THREE.MeshPhongMaterial({ color: 0x102a41, shininess: 9 }),
    );
    scene.add(earth);
    scene.add(new THREE.AmbientLight(0x95bfe1, 2));
    const light = new THREE.DirectionalLight(0x9ccfe9, 2);
    light.position.set(4, 5, 3);
    scene.add(light);
    const atmos = new THREE.Mesh(
      new THREE.SphereGeometry(1.025, 64, 48),
      new THREE.MeshBasicMaterial({
        color: 0x2c8cba,
        transparent: true,
        opacity: 0.085,
        side: THREE.BackSide,
      }),
    );
    scene.add(atmos);
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x26516a,
      transparent: true,
      opacity: 0.42,
    });
    for (let lat = -60; lat <= 60; lat += 30) {
      const pts = [];
      for (let lon = -180; lon <= 180; lon += 3) pts.push(xyz(lat, lon, 1.002));
      scene.add(
        new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat),
      );
    }
    for (let lon = -180; lon < 180; lon += 30) {
      const pts = [];
      for (let lat = -90; lat <= 90; lat += 3) pts.push(xyz(lat, lon, 1.002));
      scene.add(
        new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), lineMat),
      );
    }
    let disposed = false;
    const controller = new AbortController();
    fetch('/countries.geojson', { signal: controller.signal })
      .then((r) => r.json())
      .then((data: any) => {
        if (disposed) return;
        // Rasterize factual Natural Earth polygons into a local equirectangular texture.
        const canvas = document.createElement('canvas');
        canvas.width = 2048;
        canvas.height = 1024;
        const ctx = canvas.getContext('2d')!;
        ctx.fillStyle = '#0b2135';
        ctx.fillRect(0, 0, 2048, 1024);
        ctx.fillStyle = '#254b5c';
        ctx.strokeStyle = '#56818a';
        ctx.lineWidth = 1;
        for (const f of data.features) {
          const polys =
            f.geometry.type === 'Polygon'
              ? [f.geometry.coordinates]
              : f.geometry.coordinates;
          for (const poly of polys) {
            ctx.beginPath();
            for (const ring of poly) {
              ring.forEach(([lon, lat]: number[], i: number) => {
                const x = ((lon + 180) / 360) * 2048,
                  y = ((90 - lat) / 180) * 1024;
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
              });
              ctx.closePath();
            }
            ctx.fill('evenodd');
            ctx.stroke();
          }
        }
        const texture = new THREE.CanvasTexture(canvas);
        texture.colorSpace = THREE.SRGBColorSpace;
        (earth.material as THREE.MeshPhongMaterial).map = texture;
        (earth.material as THREE.MeshPhongMaterial).color.set(0xffffff);
        earth.material.needsUpdate = true;
      })
      .catch((e) => {
        if (e.name !== 'AbortError')
          setError(
            'Country boundaries unavailable; coordinate globe remains interactive.',
          );
      });
    const marker = new THREE.Mesh(
      new THREE.SphereGeometry(0.016, 12, 12),
      new THREE.MeshBasicMaterial({ color: 0x8cfff0 }),
    );
    scene.add(marker);
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.026, 0.031, 36),
      new THREE.MeshBasicMaterial({ color: 0x67e9db, side: THREE.DoubleSide }),
    );
    scene.add(ring);
    const overlay = new THREE.Group();
    scene.add(overlay);
    let oldCells: Row[] | null = null,
      oldEvents: Row[] | null = null,
      oldLayer = '',
      oldPlace = '';
    const particles = Array.from({ length: 180 }, () => ({
      lat: place.latitude + (Math.random() - 0.5) * 12,
      lon: place.longitude + (Math.random() - 0.5) * 12,
      age: Math.random() * 5,
    }));
    const particlePositions = new Float32Array(180 * 6);
    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute(
      'position',
      new THREE.BufferAttribute(particlePositions, 3),
    );
    const particleMesh = new THREE.LineSegments(
      particleGeo,
      new THREE.LineBasicMaterial({
        color: 0xb9fff2,
        transparent: true,
        opacity: 0.75,
      }),
    );
    scene.add(particleMesh);
    const clearOverlay = () => {
      while (overlay.children.length) {
        const obj = overlay.children[0] as THREE.Mesh;
        overlay.remove(obj);
        obj.geometry.dispose();
        (obj.material as THREE.Material).dispose();
      }
    };
    let startX = 0,
      startY = 0;
    const down = (e: PointerEvent) => {
      startX = e.clientX;
      startY = e.clientY;
    };
    const pick = (e: PointerEvent) => {
      if (Math.hypot(e.clientX - startX, e.clientY - startY) > 5) return;
      const box = el.getBoundingClientRect();
      const ray = new THREE.Raycaster();
      ray.setFromCamera(
        new THREE.Vector2(
          ((e.clientX - box.left) / box.width) * 2 - 1,
          (-(e.clientY - box.top) / box.height) * 2 + 1,
        ),
        camera,
      );
      const eventHit = ray
        .intersectObjects(overlay.children)
        .find((h) => h.object.userData.event);
      if (eventHit) {
        latest.current.onEvent?.(eventHit.object.userData.event);
        return;
      }
      const hit = ray.intersectObject(earth)[0];
      if (hit) {
        const p = hit.point.normalize(),
          lat = (Math.asin(p.y) * 180) / Math.PI,
          lon = (Math.atan2(-p.z, p.x) * 180) / Math.PI;
        latest.current.onSelect({
          latitude: Number(lat.toFixed(3)),
          longitude: Number(lon.toFixed(3)),
          name: `${lat.toFixed(2)}°, ${lon.toFixed(2)}°`,
        });
      }
    };
    renderer.domElement.addEventListener('pointerdown', down);
    renderer.domElement.addEventListener('pointerup', pick);
    actions.current = {
      zoom: (n) => camera.position.multiplyScalar(n),
      reset: () => {
        camera.position.copy(
          xyz(
            latest.current.place.latitude,
            latest.current.place.longitude,
            3.5,
          ),
        );
        controls.target.set(0, 0, 0);
      },
    };
    const resize = new ResizeObserver(() => {
      const w = el.clientWidth,
        h = el.clientHeight;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    });
    resize.observe(el);
    let frame = 0,
      last = performance.now();
    const animate = (now: number) => {
      frame = requestAnimationFrame(animate);
      if (document.hidden) return;
      const dt = Math.min((now - last) / 1000, 0.05);
      last = now;
      const state = latest.current;
      const pk = `${state.place.latitude},${state.place.longitude}`;
      if (pk !== oldPlace) {
        marker.position.copy(
          xyz(state.place.latitude, state.place.longitude, 1.025),
        );
        ring.position.copy(
          xyz(state.place.latitude, state.place.longitude, 1.028),
        );
        ring.lookAt(ring.position.clone().multiplyScalar(2));
        camera.position.copy(
          xyz(
            state.place.latitude,
            state.place.longitude,
            camera.position.length(),
          ),
        );
        oldPlace = pk;
      }
      if (
        oldCells !== state.cells ||
        oldLayer !== state.layer ||
        oldEvents !== state.events
      ) {
        clearOverlay();
        oldCells = state.cells;
        oldLayer = state.layer;
        oldEvents = state.events;
        if (fields[state.layer] && state.layer !== 'Wind')
          for (const c of state.cells) {
            const value = c[fields[state.layer]];
            if (value == null) continue;
            const [min, max] = ranges[state.layer];
            const t = Math.max(0, Math.min(1, (value - min) / (max - min)));
            const mesh = new THREE.Mesh(
              new THREE.PlaneGeometry(0.048, 0.048),
              new THREE.MeshBasicMaterial({
                color: new THREE.Color().setHSL(0.62 - t * 0.61, 0.75, 0.6),
                transparent: true,
                opacity: 0.55,
                side: THREE.DoubleSide,
              }),
            );
            mesh.position.copy(xyz(c.latitude, c.longitude, 1.009));
            mesh.lookAt(mesh.position.clone().multiplyScalar(2));
            overlay.add(mesh);
          }
        if (state.layer === 'Earthquake')
          for (const ev of state.events) {
            const mesh = new THREE.Mesh(
              new THREE.SphereGeometry(
                0.008 + Math.max(0, ev.magnitude) * 0.003,
                12,
                12,
              ),
              new THREE.MeshBasicMaterial({ color: 0xf7b276 }),
            );
            mesh.position.copy(xyz(ev.latitude, ev.longitude, 1.015));
            mesh.userData.event = ev;
            overlay.add(mesh);
          }
      }
      particleMesh.visible = state.layer === 'Wind' && state.cells.length > 0;
      if (particleMesh.visible)
        particles.forEach((p, i) => {
          let vector = interpolate(state.cells, p.lat, p.lon);
          p.age += dt;
          if (!vector || p.age > 6) {
            p.lat = state.place.latitude + (Math.random() - 0.5) * 12;
            p.lon = state.place.longitude + (Math.random() - 0.5) * 12;
            p.age = 0;
            vector = interpolate(state.cells, p.lat, p.lon);
          }
          const from = xyz(
            p.lat - (vector?.v || 0) * 0.075,
            p.lon -
              ((vector?.u || 0) * 0.075) /
                Math.max(0.15, Math.cos((p.lat * Math.PI) / 180)),
            1.014,
          );
          if (vector) {
            p.lat += vector.v * dt * 0.025;
            p.lon +=
              (vector.u * dt * 0.025) /
              Math.max(0.15, Math.cos((p.lat * Math.PI) / 180));
          }
          const to = xyz(p.lat, p.lon, 1.015);
          from.toArray(particlePositions, i * 6);
          to.toArray(particlePositions, i * 6 + 3);
        });
      particleGeo.attributes.position.needsUpdate = true;
      controls.update();
      renderer.render(scene, camera);
    };
    frame = requestAnimationFrame(animate);
    return () => {
      disposed = true;
      controller.abort();
      cancelAnimationFrame(frame);
      resize.disconnect();
      controls.dispose();
      renderer.domElement.removeEventListener('pointerdown', down);
      renderer.domElement.removeEventListener('pointerup', pick);
      scene.traverse((o) => {
        const m = o as THREE.Mesh;
        if (m.geometry) m.geometry.dispose();
        if (m.material) {
          for (const mat of Array.isArray(m.material)
            ? m.material
            : [m.material]) {
            (mat as THREE.MeshPhongMaterial).map?.dispose();
            mat.dispose();
          }
        }
      });
      renderer.dispose();
      el.replaceChildren();
    };
  }, []);
  return (
    <>
      <div
        ref={host}
        className="globe-canvas"
        role="img"
        aria-label="Interactive Earth. Drag to rotate, scroll to zoom, click to select a location."
      />
      {error && <div className="error-note">{error}</div>}
      <div className="globe-controls">
        <button
          className="icon-btn"
          aria-label="Zoom in"
          onClick={() => actions.current?.zoom(0.85)}
        >
          <Plus size={16} />
        </button>
        <button
          className="icon-btn"
          aria-label="Zoom out"
          onClick={() => actions.current?.zoom(1.15)}
        >
          <Minus size={16} />
        </button>
        <button
          className="icon-btn"
          aria-label="Reset globe camera"
          onClick={() => actions.current?.reset()}
        >
          <RotateCcw size={15} />
        </button>
      </div>
    </>
  );
}
