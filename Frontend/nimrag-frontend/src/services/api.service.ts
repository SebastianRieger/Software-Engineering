import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'

export class ApiError extends Error {
    statusCode: number
    response?: any

    constructor(statusCode: number, message: string, response?: any) {
        super(message)
        this.name = 'ApiError'
        this.statusCode = statusCode
        this.response = response
    }
}

export class ApiService {
    private static instance: ApiService
    private axiosInstance: AxiosInstance

    private constructor() {
        this.axiosInstance = axios.create({
            baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
            timeout: 10000,
            headers: {
                'Content-Type': 'application/json'
            }
        })

        this.setupInterceptors()
    }

    public static getInstance(): ApiService {
        if (!ApiService.instance) {
            ApiService.instance = new ApiService()
        }
        return ApiService.instance
    }

    private setupInterceptors(): void {
        this.axiosInstance.interceptors.request.use(
            (config) => {
                const token = localStorage.getItem('auth_token')
                if (token && config.headers) {
                    ;(config.headers as Record<string, string>).Authorization = `Bearer ${token}`
                }
                return config
            },
            (error) => Promise.reject(error)
        )

        this.axiosInstance.interceptors.response.use(
            (response) => response,
            (error) => {
                if (error.response) {
                    throw new ApiError(
                        error.response.status,
                        error.response.data?.message || 'An error occurred',
                        error.response.data
                    )
                }
                throw new ApiError(500, 'Network Error')
            }
        )
    }

    public async get<T>(endpoint: string, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.axiosInstance.get(endpoint, config)
        return response.data
    }

    public async post<T>(endpoint: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.axiosInstance.post(endpoint, data, config)
        return response.data
    }

    public async put<T>(endpoint: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.axiosInstance.put(endpoint, data, config)
        return response.data
    }

    public async delete<T>(endpoint: string, config?: AxiosRequestConfig): Promise<T> {
        const response: AxiosResponse<T> = await this.axiosInstance.delete(endpoint, config)
        return response.data
    }
}