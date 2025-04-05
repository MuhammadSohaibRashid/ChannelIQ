import React, { useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { signInWithPopup, signOut } from "firebase/auth";
import { auth, provider, db } from "../Firebase";  
import { arrayUnion, doc, setDoc, updateDoc, serverTimestamp } from "firebase/firestore";
import { UserContext } from "./UserContext";  // Import User Context
import "./LoginPage.css";
import "./base.css";

const LoginPage = () => {
  const navigate = useNavigate();
  const { user, login, logout } = useContext(UserContext);  

  // Check if user is already logged in & navigate to home
  useEffect(() => {
    if (user) {
      navigate("/home");
    }
  }, [user, navigate]);  

  const handleGoogleLogin = async () => {
    try {
        // 🔹 Step 1: Sign in with Firebase
        const result = await signInWithPopup(auth, provider);
        const user = result.user;

        // 🔹 Step 2: Get Firebase ID Token
        const idToken = await user.getIdToken(true);

        console.log("✅ Firebase Authentication Success:", user);
        console.log("🔑 Firebase ID Token:", idToken);

        // 🔹 Step 3: Send Firebase Token and User ID to Django Backend
        console.log("📤 Sending to Django Backend:", {
            token: idToken,  
            userId: user.uid   
        });

        const authResponse = await fetch("http://127.0.0.1:8000/api/auth/google-login/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: idToken, userId: user.uid })
        });

        if (!authResponse.ok) throw new Error("❌ Google login failed in Django Backend");

        const data = await authResponse.json();
        console.log("✅ Django Backend Response:", data);

        // 🔹 Step 4: Store Django Auth Token
        localStorage.setItem("authToken", data.token);

        // 🔹 Step 5: Store User Data in Firebase Firestore
        const userRef = doc(db, "users", user.uid);

        // ✅ Store basic user details (merged with existing)
        await setDoc(userRef, {
            name: user.displayName,
            email: user.email,
            profilePicture: user.photoURL,
            uid: user.uid,
            lastLogin: serverTimestamp(),  // ✅ Correct usage
        }, { merge: true });

        console.log("✅ User data saved to Firebase Firestore");

        // 🔹 Step 6: Add login history (Fixed issue with `serverTimestamp()`)
        const loginTime = new Date();  // ✅ Use normal timestamp, NOT `serverTimestamp()`
        await updateDoc(userRef, {
            loginHistory: arrayUnion(loginTime)  // ✅ Use normal timestamp instead of `serverTimestamp()`
        });

        console.log("✅ Login timestamp added to history");

        // 🔹 Step 7: Save User in Context & Local Storage
        const userData = {
            name: user.displayName,
            email: user.email,
            picture: user.photoURL,
            uid: user.uid,
            token: data.token
        };

        login(userData);
        localStorage.setItem("user", JSON.stringify(userData));

        // 🔹 Step 8: Redirect to Home Page
        navigate("/home");
    } catch (error) {
        console.error("❌ Google Login Failed:", error);
    }
};

  
  

  // ✅ Logout function (clears Firebase session)
  const handleLogout = async () => {
    try {
      await signOut(auth); // Sign out from Firebase
      logout(); // Clear user from context
      localStorage.removeItem("user"); // Remove from local storage
      navigate("/login");
    } catch (error) {
      console.error("Logout Failed", error);
    }
  };

  return (
    <div className="login-page">
      <header className="header">
        <h1 className="logo">
          <span className="bold">Channel-</span>
          <span className="highlight">IQ</span>
        </h1>
        <nav className="nav">
          {user && ( 
            <button className="sign-out" onClick={handleLogout}>
              Logout
            </button>
          )}
        </nav>
      </header>

      <div className="login-container">
        <div className="left-panel">
          <h1>
            Channel-<span className="highlight">IQ</span>
          </h1>
          <p>
            Turn your long videos into <span className="highlight">VIRAL</span> short clips.
          </p>
          <ul>
            <li>✔ AI SEO</li>
            <li>✔ Auto Caption</li>
            <li>✔ Auto Clipping</li>
            <li>✔ Quality Enhancer</li>
            <li>✔ Sound Improvement</li>
          </ul>
        </div>

        <div className="right-panel">
          <h2>{user ? `Welcome, ${user.name}` : "Login to your account"}</h2>

          {user ? (
            <button className="logout-btn" onClick={handleLogout}>
              Logout
            </button>
          ) : (
            <button className="login-btn" onClick={handleGoogleLogin}>
              Sign in with Google
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
