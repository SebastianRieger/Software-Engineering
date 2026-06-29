# Vue 3 + TypeScript + Vite

This template should help get you started developing with Vue 3 and TypeScript in Vite. The template uses Vue 3 `<script setup>` SFCs, check out the [script setup docs](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) to learn more.

Learn more about the recommended Project Setup and IDE Support in the [Vue Docs TypeScript Guide](https://vuejs.org/guide/typescript/overview.html#project-setup).

## Nimrag runtime notes

The frontend expects the backend API under `VITE_API_BASE_URL` and uses Vite's `/api` proxy during development. News, weather configuration, and startup API health checks are fetched from the backend; widgets should not call external online APIs directly.

The camera widget uses the browser MediaDevices API. Camera access requires `localhost` or HTTPS and a user permission grant. If no camera is available or permission is denied, the widget stays in the grid and shows a non-blocking unavailable state. When no saved widget layout exists, the first grid cell defaults to the camera preview.
