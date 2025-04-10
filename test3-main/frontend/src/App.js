import React, { useContext, useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import HomePage from './components/HomePage';
import Clipper from './components/clipper';
import SEO from './components/Seo';
import { clientId } from './Firebase';
import ClipPreview from './components/ClipPreview';
import OptimizeVideo from './components/optimizevideo';
import Optimizevideo_shortform from './components/optimizevideo_short_form';
import Seo_shortform from './components/Seo_shortform';
import Comparison from './components/comparsion';
import LoginPage from './components/LoginPage';
import YouTubeAuthCallback from './components/YouTubeAuthCallback';
import { UserProvider, UserContext } from "./components/UserContext";
import Dashboard from './components/Dashboard';
import VideoDashboard from "./components/videoDashboard";
import VideoDetails from "./components/videoDetails";
// ✅ Create Protected Route Component
const PrivateRoute = ({ element }) => {
  const { user } = useContext(UserContext);
  return user ? element : <Navigate to="/" />;
};

const App = () => {
  // State to store the video URL, video ID, video thumbnail, and selected features
  const [videoUrl, setVideoUrl] = useState('');
  const [videoId, setVideoId] = useState('');
  const [videoThumbnail, setVideoThumbnail] = useState('');
  const [selectedFeatures, setSelectedFeatures] = useState([]);
  
  return (
    <UserProvider> {/* ✅ User Context wraps everything */}
      <GoogleOAuthProvider clientId={clientId}>  
        <BrowserRouter>
          <Routes>
            {/* ✅ Show Login First */}
            <Route path="/" element={<LoginPage />} />
            
            {/* ✅ YouTube Auth Callback Route */}
            <Route path="/youtube-auth-callback" element={<PrivateRoute element={<YouTubeAuthCallback />} />} />
            
            {/* ✅ Protect Routes - Users must be logged in */}
            <Route path="/home" element={<PrivateRoute element={<HomePage setVideoUrl={setVideoUrl} />} />} />
            <Route path="/clipper" element={<PrivateRoute element={<Clipper setVideoUrl={setVideoUrl} setVideoId={setVideoId} setVideoThumbnail={setVideoThumbnail} setSelectedFeatures={setSelectedFeatures} />} />} />
            <Route path="/seo" element={<PrivateRoute element={<SEO videoId={videoId} videoThumbnail={videoThumbnail} />} />} />
            <Route path="/clippreview" element={<PrivateRoute element={<ClipPreview videoUrl={videoUrl} />} />} />
            <Route path="/optimizevideo" element={<PrivateRoute element={<OptimizeVideo videoUrl={videoUrl} selectedFeatures={selectedFeatures} />} />} />
            <Route path="/optimizevideo_shortform" element={<PrivateRoute element={<Optimizevideo_shortform videoUrl={videoUrl} selectedFeatures={selectedFeatures} />} />} />
            <Route path="/seo_shortform" element={<PrivateRoute element={<Seo_shortform videoId={videoId} videoThumbnail={videoThumbnail} />} />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/comparison" element={<PrivateRoute element={<Comparison />} />} />
            <Route path="/video/:userId/:videoId" element={<VideoDetails />} />
            <Route path="/dashboard" element={<VideoDashboard />} />
            {/* ✅ Handle 404 */}
            <Route path="*" element={<h2>Page Not Found</h2>} />
          </Routes>
        </BrowserRouter>
      </GoogleOAuthProvider>
    </UserProvider>
  );
};

export default App;