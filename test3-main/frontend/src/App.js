import React, { useState } from 'react';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import HomePage from './components/HomePage';
import Clipper from './components/clipper';
import SEO from './components/Seo';
import ClipPreview from './components/ClipPreview';
import OptimizeVideo from './components/optimizevideo'; // Import the OptimizeVideo component
import Optimizevideo_shortform from './components/optimizevideo_short_form';
import Seo_shortform from './components/Seo_shortform';
import Comparison from './components/comparsion';
import LoginPage from './components/LoginPage';

const App = () => {
  // State to store the video URL, video ID, video thumbnail, and selected features
  const [videoUrl, setVideoUrl] = useState('');
  const [videoId, setVideoId] = useState('');
  const [videoThumbnail, setVideoThumbnail] = useState('');
  const [selectedFeatures, setSelectedFeatures] = useState([]); // For selected features

  return (
    <GoogleOAuthProvider clientId={process.env.REACT_APP_GOOGLE_CLIENT_ID}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LoginPage />} />
          <Route
            path="/home"
            element={<HomePage setVideoUrl={setVideoUrl} />}
          />
          <Route
            path="/clipper"
            element={
              <Clipper
                setVideoUrl={setVideoUrl}
                setVideoId={setVideoId}
                setVideoThumbnail={setVideoThumbnail}
                setSelectedFeatures={setSelectedFeatures} // Pass setSelectedFeatures
              />
            }
          />
          <Route
            path="/seo"
            element={<SEO videoId={videoId} videoThumbnail={videoThumbnail} />}
          />
          <Route
            path="/clippreview"
            element={<ClipPreview videoUrl={videoUrl} />}
          />
          <Route
            path="/optimizevideo"
            element={<OptimizeVideo videoUrl={videoUrl} selectedFeatures={selectedFeatures} />} // Add the route for OptimizeVideo
          />
          <Route
            path="/optimizevideo_shortform"
            element={<Optimizevideo_shortform videoUrl={videoUrl} selectedFeatures={selectedFeatures} />} // Add the route for OptimizeVideo
          />

          <Route
            path="/seo_shortform"
            element={<Seo_shortform videoId={videoId} videoThumbnail={videoThumbnail} />}
          />
          <Route path="/comparison" element={<Comparison />} />
          <Route path="/login" element={<LoginPage />} />

          <Route path="*" element={<h2>Page Not Found</h2>} />
        </Routes>
      </BrowserRouter>
    </GoogleOAuthProvider>
  );
};

export default App;
