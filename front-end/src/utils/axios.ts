import axios, { type AxiosRequestConfig } from "axios";

const axiosService = axios.create({
  baseURL: "http://localhost:8000/",
});

export default axiosService;

export async function axiosFetch(
  endpoint: string,
  params: AxiosRequestConfig["params"],
) {
  try {
    console.log("🚀 ~ params:", params);
    console.log("🚀 ~ endpoint:", endpoint);
    const response = await axiosService.get(endpoint, { params: params });
    return response.data;
  } catch (error) {
    console.error(`Error fetching from endpoint ${endpoint}`, error);
  }
}
