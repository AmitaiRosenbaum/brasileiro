import axios, { type AxiosRequestConfig } from "axios";

const axiosService = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
});

export default axiosService;

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
