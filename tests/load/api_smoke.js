import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,
  duration: '1m',
};

const BASE = __ENV.API_BASE || 'http://localhost:8000';

export default function () {
  const health = http.get(`${BASE}/health`);
  check(health, { 'health ok': (r) => r.status === 200 });
  sleep(1);
}
