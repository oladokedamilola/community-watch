// GridWatch Service Worker
// Version: 1.0.0

const CACHE_NAME = 'gridwatch-v1.0.0';
const OFFLINE_CACHE_NAME = 'gridwatch-offline-v1';
const TILE_CACHE_NAME = 'gridwatch-tiles-v1';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/offline/',
    '/static/css/style.css',
    '/static/js/main.js',
    'https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Roboto:wght@300;400;500;700&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
    console.log('[SW] Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[SW] Caching static assets');
            return cache.addAll(STATIC_ASSETS);
        }).then(() => {
            return self.skipWaiting();
        })
    );
});

// Activate event - clean old caches
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating...');
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME && 
                        cacheName !== OFFLINE_CACHE_NAME && 
                        cacheName !== TILE_CACHE_NAME) {
                        console.log('[SW] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// Fetch event - handle requests
self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);
    
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Handle map tile caching
    if (url.pathname.includes('/basemaps.cartocdn.com/') || 
        url.hostname.includes('tile.openstreetmap.org') ||
        url.pathname.includes('/maps/')) {
        
        event.respondWith(
            caches.open(TILE_CACHE_NAME).then((cache) => {
                return cache.match(event.request).then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    return fetch(event.request).then((response) => {
                        if (response.status === 200) {
                            cache.put(event.request, response.clone());
                        }
                        return response;
                    });
                });
            }).catch(() => {
                return new Response('Map tile offline', { status: 503 });
            })
        );
        return;
    }
    
    // Handle API requests - network first with offline queue
    if (url.pathname.includes('/api/')) {
        event.respondWith(
            fetch(event.request).catch((error) => {
                console.log('[SW] API offline, queueing request:', url.pathname);
                
                // Store failed request for background sync
                return storeOfflineRequest(event.request).then(() => {
                    return new Response(JSON.stringify({
                        offline: true,
                        message: 'You are offline. This report will be submitted when you reconnect.',
                        queued: true
                    }), {
                        headers: { 'Content-Type': 'application/json' }
                    });
                });
            })
        );
        return;
    }
    
    // Handle HTML pages - network first, fallback to cache
    if (event.request.mode === 'navigate') {
        event.respondWith(
            fetch(event.request).catch(() => {
                return caches.match('/offline/');
            })
        );
        return;
    }
    
    // Handle static assets - cache first, then network
    event.respondWith(
        caches.match(event.request).then((cachedResponse) => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(event.request).then((response) => {
                // Cache valid responses
                if (response.status === 200 && event.request.url.includes('/static/')) {
                    const responseToCache = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(event.request, responseToCache);
                    });
                }
                return response;
            });
        })
    );
});

// Background Sync for offline reports
self.addEventListener('sync', (event) => {
    console.log('[SW] Background sync triggered:', event.tag);
    
    if (event.tag === 'sync-reports') {
        event.waitUntil(syncOfflineReports());
    }
});

// Function to store offline requests
async function storeOfflineRequest(request) {
    const db = await openOfflineDB();
    const transaction = db.transaction(['offlineRequests'], 'readwrite');
    const store = transaction.objectStore('offlineRequests');
    
    const clone = request.clone();
    const requestData = {
        id: Date.now(),
        url: clone.url,
        method: clone.method,
        headers: Object.fromEntries(clone.headers.entries()),
        body: await clone.text(),
        timestamp: new Date().toISOString()
    };
    
    return store.add(requestData);
}

// Function to sync offline reports
async function syncOfflineReports() {
    console.log('[SW] Syncing offline reports...');
    
    const db = await openOfflineDB();
    const transaction = db.transaction(['offlineRequests'], 'readonly');
    const store = transaction.objectStore('offlineRequests');
    const requests = await store.getAll();
    
    for (const req of requests) {
        try {
            const response = await fetch(req.url, {
                method: req.method,
                headers: req.headers,
                body: req.body
            });
            
            if (response.ok) {
                // Remove from offline store
                const deleteTransaction = db.transaction(['offlineRequests'], 'readwrite');
                const deleteStore = deleteTransaction.objectStore('offlineRequests');
                await deleteStore.delete(req.id);
                
                // Show notification to user
                self.registration.showNotification('Report Submitted!', {
                    body: 'Your offline report has been submitted successfully.',
                    icon: '/static/images/icons/icon-192.png',
                    badge: '/static/images/icons/badge.png',
                    vibrate: [200, 100, 200]
                });
            }
        } catch (error) {
            console.error('[SW] Failed to sync report:', req.id, error);
        }
    }
}

// Open IndexedDB for offline storage
function openOfflineDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('GridWatchOfflineDB', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('offlineRequests')) {
                db.createObjectStore('offlineRequests', { keyPath: 'id' });
            }
            if (!db.objectStoreNames.contains('offlineReports')) {
                db.createObjectStore('offlineReports', { keyPath: 'id' });
            }
        };
    });
}

// Push notification handling
self.addEventListener('push', (event) => {
    console.log('[SW] Push received');
    
    let data = {
        title: 'GridWatch Update',
        body: 'You have a new notification',
        icon: '/static/images/icons/icon-192.png',
        badge: '/static/images/icons/badge.png',
        vibrate: [200, 100, 200],
        data: { url: '/' }
    };
    
    if (event.data) {
        try {
            data = JSON.parse(event.data.text());
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon,
            badge: data.badge,
            vibrate: data.vibrate,
            data: data.data,
            actions: [
                { action: 'open', title: 'View Details' },
                { action: 'dismiss', title: 'Dismiss' }
            ]
        })
    );
});

// Notification click handling
self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    
    if (event.action === 'dismiss') {
        return;
    }
    
    const urlToOpen = event.notification.data?.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
            for (const client of windowClients) {
                if (client.url === urlToOpen && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
    );
});

// Message handling from main thread
self.addEventListener('message', (event) => {
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data.type === 'GET_SYNC_STATUS') {
        openOfflineDB().then((db) => {
            const transaction = db.transaction(['offlineRequests'], 'readonly');
            const store = transaction.objectStore('offlineRequests');
            const countRequest = store.count();
            
            countRequest.onsuccess = () => {
                event.ports[0].postMessage({ 
                    type: 'SYNC_STATUS', 
                    count: countRequest.result 
                });
            };
        });
    }
});