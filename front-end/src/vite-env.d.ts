/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ACKNOWLEDGMENT_NAME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
