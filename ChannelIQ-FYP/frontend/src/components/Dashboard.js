import React, { useEffect, useState, useContext } from "react";
import { collection, doc, onSnapshot } from "firebase/firestore";
import { db } from "../Firebase";
import { UserContext } from "./UserContext";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css"; // Import styles

const Dashboard = () => {
  const { user } = useContext(UserContext);
  const navigate = useNavigate();
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [optimizedVideos, setOptimizedVideos] = useState({ LongForm: null, ShortForm: null });

  // 🔄 Real-time listener for fetching ALL videos
  useEffect(() => {
    if (!user) {
      navigate("/login");
      return;
    }

    const videosRef = collection(db, "users", user.uid, "videos");
    console.log("🔍 Setting up Firestore listener for videos...");

    const unsubscribeVideos = onSnapshot(
      videosRef,
      (snapshot) => {
        console.log("📢 Firestore update detected!");
        const fetchedVideos = snapshot.docs.map((doc) => ({
          id: doc.id,
          ...doc.data(),
          createdAt: doc.data().createdAt
            ? new Date(doc.data().createdAt.seconds * 1000).toLocaleString()
            : "N/A",
        }));

        setVideos(fetchedVideos);
        setLoading(false);

        // Auto-select the first video if no video is selected
        if (fetchedVideos.length > 0 && !selectedVideo) {
          setSelectedVideo(fetchedVideos[0].id);
        }
      },
      (error) => {
        console.error("🔥 Error fetching videos:", error);
        setLoading(false);
      }
    );

    return () => unsubscribeVideos();
  }, [user, navigate]);

  // 🔄 Real-time listener for fetching the selected video’s optimized details
  useEffect(() => {
    if (!selectedVideo || !user) return;

    const longFormRef = doc(db, "users", user.uid, "videos", selectedVideo, "generate", "LongForm");
    const shortFormRef = doc(db, "users", user.uid, "videos", selectedVideo, "generate", "ShortForm");

    console.log(`📢 Listening for optimized videos of: ${selectedVideo}`);

    const unsubscribeLongForm = onSnapshot(
      longFormRef,
      (docSnap) => {
        setOptimizedVideos((prev) => ({
          ...prev,
          LongForm: docSnap.exists() ? docSnap.data() : null,
        }));
      },
      (error) => console.error("🔥 Error fetching LongForm video:", error)
    );

    const unsubscribeShortForm = onSnapshot(
      shortFormRef,
      (docSnap) => {
        setOptimizedVideos((prev) => ({
          ...prev,
          ShortForm: docSnap.exists() ? docSnap.data() : null,
        }));
      },
      (error) => console.error("🔥 Error fetching ShortForm video:", error)
    );

    return () => {
      unsubscribeLongForm();
      unsubscribeShortForm();
    };
  }, [selectedVideo, user]);

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header">
        <div className="user-info">
          <img src={user?.photoURL || "/default-profile.png"} alt="Profile" className="profile-image" />
          <div>
            <h2>Welcome, {user?.displayName}!</h2>
            <p>{user?.email}</p>
          </div>
        </div>
        <button onClick={() => alert("User login details feature coming soon!")}>View Login Details</button>
      </header>

      {/* Main Content */}
      <div className="content">
        {/* Fetched Videos Section */}
        <div className="videos-section">
          <h2>Fetched Videos</h2>
          {loading ? (
            <p className="loading">Loading videos...</p>
          ) : videos.length > 0 ? (
            <div className="video-list">
              {videos.map((video) => (
                <div
                  key={video.id}
                  className={`video-card ${selectedVideo === video.id ? "selected" : ""}`}
                  onClick={() => setSelectedVideo(video.id)}
                >
                  <h3>{video.id}</h3>
                  <p>Fetched at: {video.createdAt}</p>
                </div>
              ))}
            </div>
          ) : (
            <p className="no-videos">No videos found.</p>
          )}
        </div>

        {/* Optimized Videos Section */}
        {selectedVideo && (
          <div className="optimized-section">
            <h2>Optimized Videos for "{selectedVideo}"</h2>

            {/* Long-Form Video */}
            <div className="optimized-card">
              <h3>Long-Form Video</h3>
              {optimizedVideos.LongForm ? (
                <>
                  <div className="video-details">
                    <p><strong>Selected Features:</strong> {optimizedVideos.LongForm.selectedFeatures || "N/A"}</p>
                    <p><strong>Timestamp:</strong> {optimizedVideos.LongForm.timestamp ? new Date(optimizedVideos.LongForm.timestamp.seconds * 1000).toLocaleString() : "N/A"}</p>
                    <p><strong>Status:</strong> {optimizedVideos.LongForm.status || "N/A"}</p>
                  </div>

                  {/* Downloadable Link */}
                  {optimizedVideos.LongForm.processedVideoURL && (
                    <a href={optimizedVideos.LongForm.processedVideoURL} className="download-link" target="_blank" rel="noopener noreferrer">
                      📥 Download Long-Form Video
                    </a>
                  )}
                </>
              ) : (
                <p className="no-videos">No Long-Form video available.</p>
              )}
            </div>

            {/* Short-Form Videos */}
            <div className="optimized-card">
              <h3>Short-Form Video</h3>
              {optimizedVideos.ShortForm ? (
                <>
                  <div className="video-details">
                    <p><strong>Selected Features:</strong> {optimizedVideos.ShortForm.selectedFeatures || "N/A"}</p>
                    <p><strong>Timestamp:</strong> {optimizedVideos.ShortForm.timestamp ? new Date(optimizedVideos.ShortForm.timestamp.seconds * 1000).toLocaleString() : "N/A"}</p>
                  </div>

                  {/* Downloadable Clips */}
                  {optimizedVideos.ShortForm.processedClipPaths?.map((clip, index) => (
                    <a key={index} href={clip} className="download-link" target="_blank" rel="noopener noreferrer">
                      📥 Download Clip {index + 1}
                    </a>
                  ))}
                </>
              ) : (
                <p className="no-videos">No Short-Form video available.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
