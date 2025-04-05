import React, { useContext, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { doc, getDoc } from "firebase/firestore";
import { db } from "../Firebase";  // ✅ Import Firebase Firestore
import "./HomePage.css";
import homepageImage from "./homepage.png";
import { UserContext } from "./UserContext"; // Import global User Context

const HomePage = () => {
  const { user, logout, login } = useContext(UserContext); // Access global user state
  const navigate = useNavigate();
  const [loadingUser, setLoadingUser] = useState(true); // ✅ Loading state for Firestore

  // Refs for animation elements
  const titleRef = useRef(null);
  const subtitleRef = useRef(null);
  const previewRef = useRef(null);
  const buttonRef = useRef(null);

  // ✅ Fetch user data from Firestore if not available in context
  useEffect(() => {
    const fetchUserFromFirestore = async () => {
      if (user) {
        setLoadingUser(false);
        return; // If user is already in context, skip Firestore fetch
      }

      const storedUser = JSON.parse(localStorage.getItem("user"));
      if (storedUser?.uid) {
        try {
          const userDoc = await getDoc(doc(db, "users", storedUser.uid));
          if (userDoc.exists()) {
            console.log("User Data from Firestore:", userDoc.data());
            login(userDoc.data()); // ✅ Update global context
          }
        } catch (error) {
          console.error("Error fetching user data from Firestore:", error);
        }
      }
      setLoadingUser(false);
    };

    fetchUserFromFirestore();
  }, [user, login]);

  // ✅ Add animations when component mounts
  useEffect(() => {
    const elements = [titleRef, subtitleRef, previewRef, buttonRef];
    elements.forEach((ref, index) => {
      if (ref.current) {
        setTimeout(() => {
          ref.current.classList.add("animate-in");
        }, index * 200); // Stagger animations by 200ms
      }
    });
  }, []);

  return (
    <div className="home">
      {/* Navbar */}
      <header className="header">
        <div className="header__logo" onClick={() => navigate("/")}>
          Channel-<span className="header__logo-highlight">IQ</span>
        </div>

        {/* Show user profile if logged in, otherwise show login button */}
        {loadingUser ? (
          <p className="loading-text">Loading user...</p>
        ) : user ? (
          <div className="user">
            {user.picture && <img src={user.picture} alt="User" className="user__avatar" />}
            <span className="user__name">{user.name}</span>
            <button className="user__logout-btn" onClick={logout}>
              Logout
            </button>
          </div>
        ) : (
          <button className="user__login-btn" onClick={() => navigate("/login")}>
            Login
          </button>
        )}
      </header>

      {/* Hero Section */}
      <main className="hero">
        <h1 className="hero__title" ref={titleRef}>
          Clip your long video in <span className="hero__title-highlight">one</span>{" "}
          <span className="hero__title-click">click.</span>
        </h1>

        <p className="hero__subtitle" ref={subtitleRef}>
          <span className="hero__sparkle">✨</span> Meet Clipper, a multi-modal AI that can clip any type of video.
        </p>

        {/* Image Preview Section */}
        <div className="preview" ref={previewRef}>
          <div className="preview__shadow"></div>
          <img src={homepageImage} alt="Video clipping preview" className="preview__image" />
        </div>

        {/* "Get Clips" Button */}
        <div className="cta" ref={buttonRef}>
          <button className="cta__button" onClick={() => navigate("/clipper")}>
            Get Clips
          </button>
          <div className="cta__glow"></div>
        </div>
      </main>
    </div>
  );
};

export default HomePage;
