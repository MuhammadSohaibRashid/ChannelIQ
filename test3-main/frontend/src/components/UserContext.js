import React, { createContext, useState, useEffect } from "react";

// Create User Context
export const UserContext = createContext();

// User Provider Component
export const UserProvider = ({ children }) => {
  const [user, setUser] = useState(undefined);

  // Load user from localStorage when the app loads
  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const token = localStorage.getItem("token");
  
    if (storedUser && token) {
      setUser(JSON.parse(storedUser));
    } else {
      setUser(null);
    }
  }, []);
  

  // Login function to set user
  const login = (userData, token) => {
    setUser(userData);
    localStorage.setItem("user", JSON.stringify(userData));
    localStorage.setItem("token", token); // ✅ Save token
  };

  // Logout function to clear session
  const logout = () => {
    setUser(null);
    localStorage.removeItem("user");
  };

  return (
    <UserContext.Provider value={{ user, login, logout }}>
      {user === undefined ? null : children} {/* 🚀 Wait for user state to load */}
    </UserContext.Provider>
  );
};
