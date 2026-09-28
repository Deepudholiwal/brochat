import React from 'react';
import { Navigate } from 'react-router-dom';
import { isLoggedIn } from '../utils/api';

export default function ProtectedRoute({ children }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />;
}
