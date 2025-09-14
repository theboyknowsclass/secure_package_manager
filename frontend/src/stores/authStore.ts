import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { api } from '../services/api';

export interface User {
  sub: string;
  username: string;
  email: string;
  full_name: string;
  role: 'user' | 'approver' | 'admin';
  ad_groups: string[];
}

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  
  // Actions
  setUser: (user: User | null) => void;
  setToken: (token: string | null) => void;
  setLoading: (loading: boolean) => void;
  login: (user: User, token: string) => void;
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  devtools(
    (set, get) => ({
      user: null,
      token: null,
      loading: true,
      isAuthenticated: false,

      setUser: (user) => {
        console.log('AuthStore: Setting user:', user);
        set({ user, isAuthenticated: !!user });
      },

      setToken: (token) => {
        console.log('AuthStore: Setting token:', token ? 'present' : 'null');
        set({ token });
        
        // Update API headers
        if (token) {
          api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
        } else {
          delete api.defaults.headers.common["Authorization"];
        }
      },

      setLoading: (loading) => {
        console.log('AuthStore: Setting loading:', loading);
        set({ loading });
      },

      login: (user, token) => {
        console.log('AuthStore: Login called with user:', user, 'token:', token ? 'present' : 'null');
        set({ 
          user, 
          token, 
          isAuthenticated: true, 
          loading: false 
        });
        
        // Update API headers
        api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      },

      logout: () => {
        console.log('AuthStore: Logout called');
        set({ 
          user: null, 
          token: null, 
          isAuthenticated: false, 
          loading: false 
        });
        
        // Clear API headers
        delete api.defaults.headers.common["Authorization"];
      },

      checkAuth: () => {
        console.log('AuthStore: CheckAuth called');
        // Check if we have stored authentication data
        const storedUser = localStorage.getItem('user');
        const storedToken = localStorage.getItem('access_token');
        
        if (storedUser && storedToken) {
          try {
            const user = JSON.parse(storedUser);
            console.log('AuthStore: Found stored user:', user);
            set({ 
              user, 
              token: storedToken, 
              isAuthenticated: true, 
              loading: false 
            });
            // Update API headers
            api.defaults.headers.common["Authorization"] = `Bearer ${storedToken}`;
          } catch (error) {
            console.error('AuthStore: Error parsing stored user:', error);
            set({ loading: false });
          }
        } else {
          console.log('AuthStore: No stored authentication found');
          set({ loading: false });
        }
      },
    }),
    {
      name: 'auth-store',
    }
  )
);
