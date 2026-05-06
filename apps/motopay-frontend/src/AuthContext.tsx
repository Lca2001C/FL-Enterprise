import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [apiBase, setApiBase] = useState(localStorage.getItem('apiBase') || 'http://localhost:8000');

  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
      fetchMe();
    } else {
      localStorage.removeItem('token');
      setUser(null);
    }
  }, [token]);

  useEffect(() => {
    localStorage.setItem('apiBase', apiBase);
  }, [apiBase]);

  const fetchMe = async () => {
    try {
      const response = await axios.get(`${apiBase}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      logout();
    }
  };

  const login = async (email, password) => {
    const response = await axios.post(`${apiBase}/api/v1/auth/login`, {
      email,
      password
    });
    setToken(response.data.access_token);
    return response.data;
  };

  const logout = () => {
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, apiBase, setApiBase, login, logout, fetchMe }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
