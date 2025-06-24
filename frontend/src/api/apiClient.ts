// frontend/src/api/apiClient.ts
import axios from 'axios';

// 从环境变量获取后端的地址，如果不存在，则使用本地开发的默认地址
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

export default apiClient;