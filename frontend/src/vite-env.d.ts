/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Absolute API base URL (no trailing slash). Empty in development → Vite proxy. */
  readonly VITE_API_BASE_URL?: string;
  /** Dev-server proxy target for /api requests. */
  readonly VITE_API_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
