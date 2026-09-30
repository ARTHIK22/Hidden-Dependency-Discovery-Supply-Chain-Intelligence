const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();

export const API_BASE_URL = (configuredBaseUrl || "http://127.0.0.1:8000/api/v1").replace(/\/$/, "");
export const API_ROOT_URL = API_BASE_URL.replace(/\/api\/v1$/, "");
