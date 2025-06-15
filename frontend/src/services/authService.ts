// src/services/authService.ts
import axios from 'axios';

// Define types
export interface User {
  id: string;
  username: string;
  email: string;
  operating_system?: string;
  os_version?: string;
  cpu_cores?: number;
  total_memory?: number;
  avatar?: string;
  needs_onboarding?: boolean;
  profile?: any;
  preferences?: any;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface RefreshResponse {
  access_token: string;
  refresh_token?: string;
}

// Set up axios instance with authentication
const authApi = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/auth',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add CSRF token handling
let csrfToken: string | null = null;

// Function to get CSRF token
const getCsrfToken = async (): Promise<string | null> => {
  if (csrfToken) return csrfToken;
  
  try {
    const response = await axios.get('http://127.0.0.1:8000/api/auth/csrf-token', {
      withCredentials: true
    });
    csrfToken = response.data.csrf_token;
    return csrfToken;
  } catch (error) {
    console.error('Failed to get CSRF token:', error);
    return null;
  }
};

// Add interceptors for authentication and CSRF
authApi.interceptors.request.use(
  async (config) => {
    // Add auth token if available
    const token = localStorage.getItem('token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // Add CSRF token for non-GET requests
    if (config.method !== 'get') {
      const csrf = await getCsrfToken();
      if (csrf) {
        config.headers['X-CSRFToken'] = csrf;
      }
    }
    
    return config;
  },
  error => Promise.reject(error)
);

// Add response interceptor to handle token refresh
authApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        await authService.refreshToken();
        const token = localStorage.getItem('token');
        if (token) {
          originalRequest.headers['Authorization'] = `Bearer ${token}`;
        }
        return authApi(originalRequest);
      } catch (refreshError) {
        // Refresh failed, redirect to login
        localStorage.removeItem('token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

// Create the AuthService class
class AuthService {
  private authApi = authApi;
  
  async register(username: string, email: string, password: string): Promise<User> {
    try {
      console.log('🦔 Sir Hawkington: Registering new user:', username);
      
      const response = await this.authApi.post<LoginResponse>('/register', {
        username,
        email,
        password
      });
      
      console.log('✅ Registration response:', response.data);
      
      if (!response.data.access_token || !response.data.refresh_token) {
        throw new Error('Invalid response from server: missing tokens');
      }
      
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('refresh_token', response.data.refresh_token);
      localStorage.setItem('username', response.data.user.username);
      
      return response.data.user;
    } catch (error: any) {
      let errorMessage = 'Registration failed. Please try again.';
      
      if (error.response) {
        console.error('🚨 Registration failed - Server response:', {
          status: error.response.status,
          data: error.response.data
        });
        errorMessage = error.response.data?.detail || 
                      'Registration failed. Please try a different username or email.';
      } else if (error.request) {
        console.error('🚨 Registration failed - No response:', error.request);
        errorMessage = 'Server connection error. Please try again later.';
      } else {
        console.error('🚨 Registration setup failed:', error.message);
      }
      
      throw new Error(errorMessage);
    }
  }
  
  getCurrentUser(): User | null {
    try {
      const username = localStorage.getItem('username');
      const token = localStorage.getItem('token');
      
      if (!username || !token) {
        console.log('🦔 Sir Hawkington: No user data in localStorage');
        return null;
      }
      
      // Decode the JWT token to get user information
      const tokenPayload = JSON.parse(atob(token.split('.')[1]));
      
      if (!tokenPayload.sub) {
        console.error('🚨 Invalid token payload:', tokenPayload);
        return null;
      }
      
      // Create a user object from the token payload
      const user: User = {
        id: tokenPayload.user_id || tokenPayload.sub,
        username: tokenPayload.sub,
        email: tokenPayload.email || '',
        operating_system: tokenPayload.operating_system,
        os_version: tokenPayload.os_version,
        cpu_cores: tokenPayload.cpu_cores,
        total_memory: tokenPayload.total_memory
      };
      
      console.log('🦔 Sir Hawkington: Current user from token:', user);
      return user;
    } catch (error) {
      console.error('🚨 Error getting current user:', error);
      return null;
    }
  }
  
  updateProfile: any;
  
  async getCurrentToken(): Promise<string | null> {
    // First try to get from localStorage
    const token = localStorage.getItem('token');
    
    if (!token) {
      console.log('🦔 Sir Hawkington: No token in localStorage');
      return null;
    }
    
    // Check if token is expired
    if (this.isTokenExpired(token)) {
      console.log('🦔 Sir Hawkington: Token is expired, attempting to refresh...');
      try {
        await this.refreshToken();
        const newToken = localStorage.getItem('token');
        console.log('🦔 Sir Hawkington: Token refreshed successfully:', newToken ? `${newToken.substring(0, 20)}...` : 'null');
        return newToken;
      } catch (error) {
        console.error('🚨 Failed to refresh token:', error);
        return null; // Return the expired token as fallback - the backend will handle rejection
      }
    }
    
    console.log('🦔 Sir Hawkington: Token is valid, returning it');
    return token;
  }
  
  private isTokenExpired(token: string): boolean {
    if (!token) return true;
    
    try {
      const decoded = JSON.parse(atob(token.split('.')[1]));
      const currentTime = Math.floor(Date.now() / 1000);
      return decoded.exp < currentTime;
    } catch (error) {
      console.error('Error decoding token:', error);
      return true;
    }
  }
  
  async refreshToken(): Promise<void> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }
    
    try {
      const response = await axios.post<RefreshResponse>(
        'http://127.0.0.1:8000/api/auth/refresh/',
        { refresh_token: refreshToken },
        { withCredentials: true }
      );
      
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        if (response.data.refresh_token) {
          localStorage.setItem('refresh_token', response.data.refresh_token);
        }
      }
    } catch (error) {
      console.error('Error refreshing token:', error);
      throw error;
    }
  }
  
  async checkStatus(): Promise<boolean> {
    try {
      console.log('🦔 Sir Hawkington: Checking authentication status...');
      const response = await this.authApi.get('/status/');
      console.log('🦔 Auth status check response:', response.data);
      return response.data.is_authenticated;
    } catch (error: any) {
      console.error('🚨 Auth status check failed:', error);
      return false;
    }
  }
  
  async login(username: string, password: string): Promise<User> {
    try {
      console.log('🦔 Sir Hawkington: Logging in with username:', username);
      
      const formData = new URLSearchParams();
      formData.append('username', username);
      formData.append('password', password);
      
      const response = await axios.post<LoginResponse>(
        'http://127.0.0.1:8000/api/auth/token',
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded'
          },
          withCredentials: true
        }
      );
      
      console.log('✅ Login response:', response.data);
      
      if (!response.data.access_token || !response.data.refresh_token) {
        throw new Error('Invalid response from server: missing tokens');
      }
      
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('refresh_token', response.data.refresh_token);
      localStorage.setItem('username', response.data.user.username);
      
      axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`;
      
      return response.data.user;
    } catch (error: any) {
      let errorMessage = 'Authentication failed. Please try again.';
      
      if (error.response) {
        console.error('🚨 Login failed - Server response:', {
          status: error.response.status,
          data: error.response.data
        });
        errorMessage = error.response.data?.detail || 
                       'Authentication failed. Please check your username and password.';
      } else if (error.request) {
        console.error('🚨 Login failed - No response:', error.request);
        errorMessage = 'The Quantum Shadow People blocked your request. Please try again later.';
      } else {
        console.error('🚨 Login setup failed:', error.message);
      }
      
      throw new Error(errorMessage);
    }
  }
  
  async logout(): Promise<boolean> {
    try {
      console.log('🦔 Sir Hawkington: Logging out...');
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('username');
      csrfToken = null; // Clear CSRF token
      console.log('🐌 The Meth Snail: Local storage cleared, redirecting to login page');
      window.location.href = '/login';
      return true;
    } catch (error: any) {
      console.error('🚨 Logout failed:', error);
      localStorage.removeItem('token');
      localStorage.removeItem('refresh_token');
      localStorage.removeItem('username');
      csrfToken = null;
      window.location.href = '/login';
      return false;
    }
  }
  
  // Method to initialize connection (website first, then auth)
  async initializeConnection(): Promise<boolean> {
    try {
      // First, ensure basic connection to the website
      console.log('🦔 Initializing connection to website...');
      
      // Try to get CSRF token (this establishes basic connection)
      const csrf = await getCsrfToken();
      if (!csrf) {
        console.warn('🚨 Failed to get CSRF token, but continuing...');
      }
      
      // Then check authentication status
      const isAuthenticated = await this.checkStatus();
      console.log('🦔 Authentication status:', isAuthenticated);
      
      return isAuthenticated;
    } catch (error) {
      console.error('🚨 Failed to initialize connection:', error);
      return false;
    }
  }
}

// Export a single instance
const authService = new AuthService();
export default authService;