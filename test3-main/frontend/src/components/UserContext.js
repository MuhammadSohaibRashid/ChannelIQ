import React, { createContext, useState, useEffect } from "react";


// Create User Context
export const UserContext = createContext();

// User Provider Component
export const UserProvider = ({ children }) => {
  const [user, setUser] = useState(undefined);  // `undefined` to show loading state

  // Load user from localStorage when the app loads
  useEffect(() => {
    const storedUser = localStorage.getItem("user");
    const storedToken = localStorage.getItem("token");
  
    if (storedUser && storedToken) {
      setUser(JSON.parse(storedUser));
    } else {
      setUser(null);
    }
  }, []);
  
  // ✅ Login function to set user & store token
  const login = (userData) => {
    if (!userData || !userData.token) {
        console.error("❌ Error: Missing userData or token in login function");
        return;
    }

    const formattedUser = {
        ...userData,
        uid: userData.uid || userData.firebase_uid || userData.id || null,  // ✅ Ensure `uid` is always set
    };

    setUser(formattedUser);
    localStorage.setItem("user", JSON.stringify(formattedUser));
    localStorage.setItem("token", userData.token);
};

  // ✅ Logout function to clear session
  const logout = () => {
    setUser(null);
    localStorage.removeItem("user");
    localStorage.removeItem("token");  // ✅ Clear token on logout
  };

  return (
    <UserContext.Provider value={{ user, login, logout }}>
      {user === undefined ? null : children} {/* 🚀 Wait for user state to load */}
    </UserContext.Provider>
  );



 
};
