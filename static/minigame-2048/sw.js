/* 休闲花园 · 2048 的**局部**离线缓存。

   只缓存这一页需要的静态资源（页面外壳 / CSS / JS / 图标）：
   不缓存登录响应、令牌、账号资料、管理页面、奖励接口，也不接管 GTN 的其他页面。
   接口请求一律直连网络：断网时由页面自己显示"离线，本地已保存"，
   收到真实 401/403 时页面走身份/权限处理——**不会**拿缓存假装成功。 */

const CACHE = 'gtn-mg2048-v1';
const SHELL = [
  '/minigame/2048',
  '/static/css/minigame_2048.css',
  '/static/js/minigame_2048.js',
  '/static/assets/favicon.ico',
];

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.all(SHELL.map(async (url) => {
      try {
        const response = await fetch(url, { credentials: 'same-origin' });
        if (response.ok) await cache.put(url, response.clone());
      } catch (_) { /* 首次就离线：能缓存多少算多少 */ }
    }));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  // 接口直连：离线时交给页面处理，绝不返回缓存伪造成功
  if (url.pathname.startsWith('/api/')) return;
  const isShell = url.pathname === '/minigame/2048';
  const isAsset = url.pathname.startsWith('/static/css/minigame_2048.css')
    || url.pathname.startsWith('/static/js/minigame_2048.js')
    || url.pathname.startsWith('/static/assets/favicon.ico');
  if (!isShell && !isAsset) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const response = await fetch(request, { credentials: 'same-origin' });
      if (response.ok) cache.put(request, response.clone());
      return response;                       // 联网优先：身份变化立刻生效
    } catch (error) {
      const cached = await cache.match(request, { ignoreSearch: true });
      if (cached) return cached;
      throw error;
    }
  })());
});
