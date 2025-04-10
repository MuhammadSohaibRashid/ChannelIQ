import React, { useContext, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { signInWithPopup } from "firebase/auth";
import { auth, provider, db } from "../Firebase";
import { arrayUnion, doc, setDoc, updateDoc } from "firebase/firestore";
import { UserContext } from "./UserContext";
import "./LoginPage.css";

const LoginPage = () => {
  const navigate = useNavigate();
  const { user, login } = useContext(UserContext);

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

      // 🔹 Step 3: Send Firebase Token and User ID to Django Backend
      const authResponse = await fetch(
        "http://127.0.0.1:8000/api/auth/google-login/",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: idToken, userId: user.uid }),
        }
      );

      if (!authResponse.ok)
        throw new Error("❌ Google login failed in Django Backend");

      const data = await authResponse.json();
      console.log("✅ Django Backend Response:", data);

      // 🔹 Step 4: Store Django Auth Token
      localStorage.setItem("authToken", data.token);

      // 🔹 Step 5: Store User Data in Firebase Firestore
      const userRef = doc(db, "users", user.uid);

      // ✅ Store basic user details (merged with existing)
      await setDoc(
        userRef,
        {
          name: user.displayName,
          email: user.email,
          profilePicture: user.photoURL,
          uid: user.uid,
          lastLogin: new Date(),
        },
        { merge: true }
      );

      // 🔹 Step 6: Add login history
      const loginTime = new Date();
      await updateDoc(userRef, {
        loginHistory: arrayUnion(loginTime),
      });

      // 🔹 Step 7: Save User in Context & Local Storage
      const userData = {
        name: user.displayName,
        email: user.email,
        picture: user.photoURL,
        uid: user.uid,
        token: data.token,
      };

      login(userData);
      localStorage.setItem("user", JSON.stringify(userData));

      // 🔹 Step 8: Redirect to Home Page
      navigate("/home");
    } catch (error) {
      console.error("❌ Google Login Failed:", error);
    }
  };

  return (
    <div className="login-page">
      <div className="login-wrapper">
        {/* Left side marketing content */}
        <div className="marketing-panel">
          
          <div className="marketing-content">
            <h1 className="main-title">
              Turn your long videos into <br /> <span className="highlight">VIRAL</span> short clips
            </h1>
            
            <div className="tag-badge">#1 AI VIDEO CLIPPING TOOL</div>
            
            <h2 className="trust-text">
              Trusted by <span className="highlight">50+</span> creators and businesses worldwide
            </h2>
            
            <div className="featurex-list">
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>AI SEO</span>
              </div>
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>Auto Caption</span>
              </div>
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>Auto Clipping</span>
              </div>
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>Quality Enhancer</span>
              </div>
              <div className="featurex-item">
                <div className="featurex-icon">✔</div>
                <span>Sound Improvement</span>
              </div>
            </div>
            
            
          </div>
        </div>

        {/* Right side login form */}
        <div className="login-panel">
          <div className="login-form">
            <h1 className="channel-iq-logo">
            Channel-<span className="highlight">IQ</span>
            </h1>
            <h3 className="login-title">
              Sign up to get viral clips
            </h3>
            <p className="login-subtitle">
              Free plan available. No credit card required.
            </p>

            <button className="google-signin-btn" onClick={handleGoogleLogin}>
              <svg className="google-icon" viewBox="0 0 48 48">
                <path fill="#FFC107" d="M43.611,20.083H42V20H24v8h11.303c-1.649,4.657-6.08,8-11.303,8c-6.627,0-12-5.373-12-12c0-6.627,5.373-12,12-12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C12.955,4,4,12.955,4,24c0,11.045,8.955,20,20,20c11.045,0,20-8.955,20-20C44,22.659,43.862,21.35,43.611,20.083z"></path>
                <path fill="#FF3D00" d="M6.306,14.691l6.571,4.819C14.655,15.108,18.961,12,24,12c3.059,0,5.842,1.154,7.961,3.039l5.657-5.657C34.046,6.053,29.268,4,24,4C16.318,4,9.656,8.337,6.306,14.691z"></path>
                <path fill="#4CAF50" d="M24,44c5.166,0,9.86-1.977,13.409-5.192l-6.19-5.238C29.211,35.091,26.715,36,24,36c-5.202,0-9.619-3.317-11.283-7.946l-6.522,5.025C9.505,39.556,16.227,44,24,44z"></path>
                <path fill="#1976D2" d="M43.611,20.083H42V20H24v8h11.303c-0.792,2.237-2.231,4.166-4.087,5.571c0.001-0.001,0.002-0.001,0.003-0.002l6.19,5.238C36.971,39.205,44,34,44,24C44,22.659,43.862,21.35,43.611,20.083z"></path>
              </svg>
              Continue with Google
            </button>

            <div className="divider">
              <span>or</span>
            </div>

           

            <div className="terms-text">
              By continuing, you agree to <span className="highlight">Channel-IQ's</span> Terms of Service.
              <br />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;