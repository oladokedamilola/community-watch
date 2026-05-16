// GridWatch Offline Queue Manager
// Handles storing and syncing reports when offline

class OfflineQueueManager {
    constructor() {
        this.dbName = 'GridWatchOfflineDB';
        this.dbVersion = 1;
        this.db = null;
        this.syncInProgress = false;
        this.init();
    }
    
    async init() {
        await this.openDB();
        this.setupEventListeners();
        this.checkPendingReports();
    }
    
    openDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);
            
            request.onerror = () => reject(request.error);
            
            request.onsuccess = () => {
                this.db = request.result;
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                if (!db.objectStoreNames.contains('offlineReports')) {
                    const store = db.createObjectStore('offlineReports', { 
                        keyPath: 'id', 
                        autoIncrement: true 
                    });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('synced', 'synced', { unique: false });
                }
            };
        });
    }
    
    async saveOfflineReport(reportData) {
        if (!this.db) await this.openDB();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['offlineReports'], 'readwrite');
            const store = transaction.objectStore('offlineReports');
            
            const report = {
                ...reportData,
                timestamp: new Date().toISOString(),
                synced: false,
                retryCount: 0
            };
            
            const request = store.add(report);
            
            request.onsuccess = () => {
                console.log('[OfflineQueue] Report saved for later sync');
                this.showQueuedNotification();
                resolve(request.result);
            };
            
            request.onerror = () => reject(request.error);
        });
    }
    
    async getPendingReports() {
        if (!this.db) await this.openDB();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['offlineReports'], 'readonly');
            const store = transaction.objectStore('offlineReports');
            const index = store.index('synced');
            const pending = [];
            
            index.openCursor(IDBKeyRange.only(false)).onsuccess = (event) => {
                const cursor = event.target.result;
                if (cursor) {
                    pending.push(cursor.value);
                    cursor.continue();
                } else {
                    resolve(pending);
                }
            };
            
            transaction.onerror = () => reject(transaction.error);
        });
    }
    
    async syncPendingReports() {
        if (this.syncInProgress) {
            console.log('[OfflineQueue] Sync already in progress');
            return;
        }
        
        this.syncInProgress = true;
        
        try {
            const pendingReports = await this.getPendingReports();
            
            if (pendingReports.length === 0) {
                console.log('[OfflineQueue] No pending reports to sync');
                return;
            }
            
            console.log(`[OfflineQueue] Syncing ${pendingReports.length} reports`);
            
            for (const report of pendingReports) {
                await this.syncReport(report);
            }
            
            this.updateSyncStatus();
            
        } catch (error) {
            console.error('[OfflineQueue] Sync error:', error);
        } finally {
            this.syncInProgress = false;
        }
    }
    
    async syncReport(report) {
        try {
            const response = await fetch('/reports/api/submit/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(report.data)
            });
            
            if (response.ok) {
                // Mark as synced and delete
                await this.deleteReport(report.id);
                
                console.log(`[OfflineQueue] Report ${report.id} synced successfully`);
                
                // Show success notification
                this.showSyncNotification(true, report);
                
            } else {
                // Increment retry count
                await this.incrementRetryCount(report);
                console.log(`[OfflineQueue] Report ${report.id} sync failed, retry ${report.retryCount + 1}`);
            }
        } catch (error) {
            await this.incrementRetryCount(report);
            console.error(`[OfflineQueue] Report ${report.id} sync error:`, error);
        }
    }
    
    async deleteReport(id) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['offlineReports'], 'readwrite');
            const store = transaction.objectStore('offlineReports');
            const request = store.delete(id);
            
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }
    
    async incrementRetryCount(report) {
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['offlineReports'], 'readwrite');
            const store = transaction.objectStore('offlineReports');
            
            report.retryCount++;
            if (report.retryCount >= 5) {
                // Mark as failed after 5 attempts
                report.failed = true;
            }
            
            const request = store.put(report);
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }
    
    async checkPendingReports() {
        const pending = await this.getPendingReports();
        if (pending.length > 0) {
            this.showPendingBanner(pending.length);
            // Auto-sync when online
            if (navigator.onLine) {
                await this.syncPendingReports();
            }
        }
    }
    
    showQueuedNotification() {
        const banner = document.getElementById('offlineBanner');
        if (banner) {
            banner.style.display = 'block';
            const count = document.getElementById('pendingCount');
            if (count) {
                this.getPendingReports().then(pending => {
                    count.textContent = pending.length;
                });
            }
        }
    }
    
    showPendingBanner(count) {
        let banner = document.getElementById('offlineBanner');
        
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'offlineBanner';
            banner.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: var(--accent);
                color: var(--secondary);
                padding: 0.75rem 1rem;
                border-radius: 2rem;
                font-size: 0.8rem;
                font-weight: 600;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                z-index: 9998;
                cursor: pointer;
                display: none;
            `;
            banner.innerHTML = `
                <i class="fas fa-cloud-upload-alt"></i>
                <span id="pendingCount">${count}</span> report(s) pending sync
            `;
            
            banner.addEventListener('click', () => this.syncPendingReports());
            document.body.appendChild(banner);
        }
        
        document.getElementById('pendingCount').textContent = count;
        banner.style.display = 'block';
    }
    
    showSyncNotification(success, report) {
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(success ? 'Report Synced' : 'Sync Failed', {
                body: success 
                    ? `Report from ${report.data.location} submitted successfully` 
                    : `Failed to sync report. Will retry later.`,
                icon: '/static/images/icons/icon-192.png'
            });
        }
    }
    
    updateSyncStatus() {
        this.getPendingReports().then(pending => {
            const banner = document.getElementById('offlineBanner');
            if (banner) {
                if (pending.length === 0) {
                    banner.style.display = 'none';
                } else {
                    document.getElementById('pendingCount').textContent = pending.length;
                }
            }
        });
    }
    
    setupEventListeners() {
        // Listen for online/offline events
        window.addEventListener('online', () => {
            console.log('[OfflineQueue] Online event detected');
            this.syncPendingReports();
        });
        
        window.addEventListener('offline', () => {
            console.log('[OfflineQueue] Offline event detected');
        });
        
        // Background sync registration
        if ('serviceWorker' in navigator && 'SyncManager' in window) {
            navigator.serviceWorker.ready.then(registration => {
                registration.sync.register('sync-reports').catch(err => {
                    console.error('[OfflineQueue] Background sync registration failed:', err);
                });
            });
        }
    }
    
    getCSRFToken() {
        const cookieValue = document.cookie
            .split('; ')
            .find(row => row.startsWith('csrftoken='));
        return cookieValue ? cookieValue.split('=')[1] : '';
    }
}

// Initialize offline queue manager
let offlineQueue;

if ('serviceWorker' in navigator) {
    document.addEventListener('DOMContentLoaded', () => {
        offlineQueue = new OfflineQueueManager();
        
        // Expose for debugging
        window.offlineQueue = offlineQueue;
    });
}