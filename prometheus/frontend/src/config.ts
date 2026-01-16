/**
 * 🔧 DAVINCI FRONTEND CONFIGURATION
 * 
 * Centralized configuration for API endpoints supporting both
 * development (localhost) and production (Cloudflare tunnel) environments.
 */

// Environment detection - Vite sets import.meta.env.MODE
const isDevelopment = typeof window !== 'undefined' && window.location.hostname === 'localhost';

// API Configuration
export const API_CONFIG = {
    development: {
        apiUrl: 'http://127.0.0.1:8099',
        wsUrl: 'ws://127.0.0.1:8099',
        frontendUrl: 'http://localhost:5173'
    },
    production: {
        apiUrl: 'https://api.davinciai.eu',
        wsUrl: 'wss://api.davinciai.eu',
        frontendUrl: 'https://dashboard.davinciai.eu'
    }
};

// Active configuration based on environment
const baseConfig = isDevelopment
    ? API_CONFIG.development
    : API_CONFIG.production;

// Tenant Detection Helper
const getTenantId = () => {
    if (typeof window === 'undefined') return 'default-tenant';

    // 1. Try URL search params (?tenant=...)
    const urlParams = new URLSearchParams(window.location.search);
    const paramTenant = urlParams.get('tenant');
    if (paramTenant) return paramTenant;

    // 2. Try subdomain (tenant.davinciai.eu)
    const hostParts = window.location.hostname.split('.');
    if (hostParts.length > 2 && hostParts[0] !== 'www' && hostParts[0] !== 'dashboard') {
        return hostParts[0];
    }

    return 'default-tenant';
};

export const config = {
    ...baseConfig,
    tenantId: getTenantId()
};

// Environment helpers
export const isProduction = !isDevelopment;
export const isDev = isDevelopment;

// Log current environment on load
console.log(`🔥 DaVinci Frontend - ${isDevelopment ? 'DEVELOPMENT' : 'PRODUCTION'} MODE`);
console.log(`   API: ${config.apiUrl}`);
console.log(`   WebSocket: ${config.wsUrl}`);
