/* 休闲花园 ·「合成大花花」的**局部**离线缓存（scope=/minigame/suika）。

   只缓存这一页的静态资源（页面外壳脚本 / 样式 / 物理引擎 / 贴图）：
   不缓存登录响应、令牌、账号资料、管理页面，也不接管 GTN 的其他页面。
   接口请求直连网络，断网时由页面自己显示状态——不会拿缓存假装成功。

   注意：文档本身不缓存（页面是按账号渲染的，缓存后换账号会拿到旧配置），
   与 2048 那套保持一致。 */

const CACHE = 'gtn-mgsuika-v1';
const SHELL = [
  '/static/css/minigame_suika.css',
  '/static/js/minigame_suika.js',
  '/static/js/minigame-presence.js',
  '/static/js/suika_core.js',
  '/static/vendor/matter.min.js',
  '/static/vendor/socket.io.min.js',
  '/static/assets/favicon.ico',
  '/static/assets/story-enemies/bubble.svg',
  '/static/assets/story-enemies/ant-egg.svg',
  '/static/assets/story-enemies/ladybug.svg',
  '/static/assets/story-enemies/ant-hole.svg',
  '/static/assets/story-enemies/dark-ladybug.svg',
  '/static/assets/story-enemies/cactus.svg',
  '/static/assets/story-enemies/uranium-barrel.svg',
  '/static/assets/story-enemies/gambler.svg',
  '/static/assets/story-enemies/shiny-ladybug.svg',
  '/static/assets/story-enemies/mechanical-flower.svg',
];

const ASSET_DESTINATIONS = new Set(['script', 'style', 'image', 'font', 'manifest']);

/* 统一按"路径"存与取：带 ?v= 的资源在线时永远拿新版，离线时用最近一次存下的那份。 */
const cacheKeyFor = (request) => {
  const url = new URL(request.url);
  return new Request(`${url.origin}${url.pathname}`, { method: 'GET' });
};

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    await Promise.all(SHELL.map(async (path) => {
      try {
        const response = await fetch(path, { credentials: 'same-origin' });
        if (response.ok) {
          await cache.put(new Request(`${self.location.origin}${path}`, { method: 'GET' }), response.clone());
        }
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
  // 页面外壳按账号渲染，永远走网络
  if (url.pathname === '/minigame/suika' || request.destination === 'document') return;
  const isAsset = url.pathname.startsWith('/static/')
    || url.pathname.startsWith('/fonts/')
    || ASSET_DESTINATIONS.has(request.destination);
  if (!isAsset) return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const key = cacheKeyFor(request);
    try {
      const response = await fetch(request, { credentials: 'same-origin' });
      if (response.ok) cache.put(key, response.clone());
      return response;
    } catch (error) {
      const cached = await cache.match(key, { ignoreSearch: true });
      if (cached) return cached;
      throw error;
    }
  })());
});
