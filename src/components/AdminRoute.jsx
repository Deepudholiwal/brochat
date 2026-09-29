import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { API_BASE, isLoggedIn } from '../utils/api';

export default function AdminRoute({ children }) {
  const [role, setRole] = useState('checking');

  useEffect(() => {
    const token = localStorage.getItem('brochat_token');
    if (!token) {
      setRole('signed-out');
      return;
    }

    let active = true;
    fetch(`${API_BASE}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error('Could not verify administrator access');
        return response.json();
      })
      .then((user) => {
        if (active) setRole(user.role === 'admin' ? 'admin' : 'user');
      })
      .catch(() => {
        if (active) setRole(isLoggedIn() ? 'user' : 'signed-out');
      });

    return () => { active = false; };
  }, []);

  if (role === 'checking') return <div className="loading-screen">Checking administrator access...</div>;
  if (role === 'signed-out') return <Navigate to="/admin/login" replace />;
  if (role !== 'admin') return <Navigate to="/dashboard" replace />;
  return children;
}