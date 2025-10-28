// trino_poll.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,
  duration: '4m',
  insecureSkipTLSVerify: true,
}; // 自行調整併發/時間

const BASE = 'https://127.0.0.1:8443';
const TOKEN = __ENV.TOKEN;

export default function () {
  const h = { Authorization: `Bearer ${TOKEN}`, 'Content-Type': 'text/plain' };

  // 1) 提交 SQL
  let res = http.post(`${BASE}/v1/statement`, 'SELECT 1', { headers: h });
  check(res, { 'submit ok': (r) => r.status === 200 });

  // 2) 追 nextUri 直到沒有
  let next = res.json('nextUri');
  while (next) {
    res = http.get(next, { headers: { Authorization: `Bearer ${TOKEN}` } });
    check(res, { 'poll ok': (r) => r.status === 200 });
    next = res.json('nextUri'); // 沒有就結束
    sleep(0.1); // 避免過度緊密輪詢
  }
}
