import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './TermsAndServices.css'; // Optional: for styling

const TermsAndServices = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleClose = () => {
    // Check if there's a referrer state (page that directed to terms)
    const referrerPath = location.state?.from || '/';
    navigate(referrerPath);
  };

  // Alternative close handler that uses browser history to go back
  const handleGoBack = () => {
    navigate(-1); // Go back one step in history
  };

  return (
    <div className="terms-container">
      {/* Close Button */}
      <button className="close-button" onClick={handleGoBack}>
        ❌ Close
      </button>

      <h1>Terms and Services</h1>
      <p>Last updated: April 15, 2025</p>

      <section>
        <h2>1. Introduction</h2>
        <p>
          Welcome to ChannelIQ – an AI-powered video optimization platform designed to help creators
          enhance and manage their YouTube content and head towards an automation era. By using our tool, you agree to the terms
          outlined in this document. Please read them carefully.
        </p>
      </section>

      <section>
        <h3>Services We Provide</h3>
        <ul>
          <li>AI-based video optimization for SEO, Noise reduction and Video Quality Enhancement.</li>
          <li>Automatic captioning and clip generation using Whisper API.</li>
          <li>YouTube integration to fetch and upload videos using YouTube Data API.</li>
          <li>Storage of processed videos and clips on AWS S3.</li>
          <li>Comparative analysis between original and optimized videos.</li>
        </ul>
      </section>

      <section>
        <h2>3. Data Collection & Usage</h2>
        <p>We collect and store the following user data:</p>
        <ul>
          <li>OAuth-authenticated user information from Google (YouTube access).</li>
          <li>Uploaded or fetched video metadata (title, URL, thumbnails, etc.).</li>
          <li>Generated video content and optimization results.</li>
          <li>AI-generated SEO data like titles, descriptions, keywords, and tags.</li>
        </ul>
        <p>
          We use this data solely for optimizing your content and storing results under your
          account. All personal and video data is secured in Firebase and AWS.
        </p>
      </section>

      <section>
        <h2>4. User Responsibilities</h2>
        <ul>
          <li>You must comply with YouTube's Terms of Service and API usage policies.</li>
          <li>You agree not to misuse the platform for copyright-infringing content.</li>
          <li>You are responsible for the content you fetch, generate, or upload via our tool.</li>
        </ul>
      </section>

      <section>
        <h2>5. Third-Party Services</h2>
        <p>
          Our tool integrates with third-party APIs and services such as:
        </p>
        <ul>
          <li><strong>YouTube Data API</strong> – to access and manage your video content.</li>
          <li><strong>OpenAI & Whisper APIs</strong> – for AI-based enhancements and captioning.</li>
          <li><strong>Firebase & Firestore</strong> – for user authentication and structured data storage.</li>
          <li><strong>AWS S3</strong> – for scalable and cost-effective video file storage.</li>
        </ul>
      </section>

      <section>
        <h2>6. Termination of Service</h2>
        <p>
          We reserve the right to suspend or terminate access to our services if you are found in
          violation of our terms, misuse our APIs, or engage in malicious activity.
        </p>
      </section>

      <section>
        <h2>7. Limitation of Liability</h2>
        <p>
          ChannelIQ does not guarantee 100% accuracy in AI-generated outputs. We are not liable for
          any content loss, copyright strikes, or issues arising due to the use of processed videos.
        </p>
      </section>

      <section>
        <h2>8. Updates to These Terms</h2>
        <p>
          We may update these terms occasionally. Continued use of the platform after changes are
          made implies your acceptance of the new terms.
        </p>
      </section>

      <section>
        <h2>9. Contact Information</h2>
        <p>If you have any questions or concerns, please contact us at support@channeliq.ai</p>
      </section>
    </div>
  );
};

export default TermsAndServices;