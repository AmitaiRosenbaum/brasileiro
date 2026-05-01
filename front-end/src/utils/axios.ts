import axios, { type AxiosRequestConfig } from "axios";

const axiosService = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  withCredentials: true,
});

export default axiosService;

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export function getCsrfToken() {
  return csrfToken;
}

export async function axiosPost<ResponseType, RequestType>(
  endpoint: string,
  data: RequestType,
  config?: AxiosRequestConfig<RequestType>,
) {
  const response = await axiosService.post<ResponseType>(endpoint, data, {
    ...config,
    headers: {
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...config?.headers,
    },
  });

  return response.data;
}

export async function axiosPatch<ResponseType, RequestType>(
  endpoint: string,
  data: RequestType,
  config?: AxiosRequestConfig<RequestType>,
) {
  const response = await axiosService.patch<ResponseType>(endpoint, data, {
    ...config,
    headers: {
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...config?.headers,
    },
  });

  return response.data;
}

export async function axiosDelete<ResponseType>(
  endpoint: string,
  config?: AxiosRequestConfig,
) {
  const response = await axiosService.delete<ResponseType>(endpoint, {
    ...config,
    headers: {
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...config?.headers,
    },
  });

  return response.data;
}

export async function axiosFetch<ResponseType>(
  endpoint: string,
  params: AxiosRequestConfig["params"],
) {
  try {
    const response = await axiosService.get(endpoint, { params: params });
    return response.data as ResponseType;
  } catch (error) {
    console.error(`Error fetching from endpoint ${endpoint}`, error);
  }
}
