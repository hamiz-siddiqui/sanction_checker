// src/FileUpload.jsx
import React, { useState, useRef } from "react";
import Webcam from "react-webcam";
import "./App.css";

// Add Montserrat font import for the whole app
const fontLink = document.createElement("link");
fontLink.href =
  "https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;800&display=swap";
fontLink.rel = "stylesheet";
document.head.appendChild(fontLink);

const API_URL =
  import.meta.env.VITE_API_URL || "https://sanction-checker.onrender.com";
console.log("API_URL:", API_URL);

const FileUpload = () => {
  const [file, setFile] = useState(null);
  const [imageSrc, setImageSrc] = useState(null);
  const [fullName, setFullName] = useState("");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [showWebcam, setShowWebcam] = useState(false);
  const [showLinks, setShowLinks] = useState(false);

  const webcamRef = useRef(null);
  const fileInputRef = useRef(null);

  const clearOtherInputs = (inputType) => {
    if (inputType !== "file") {
      setFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
    if (inputType !== "webcam") {
      setImageSrc(null);
      // Optionally hide webcam if another input is used
      // setShowWebcam(false);
    }
    if (inputType !== "name") {
      setFullName("");
    }
    setResult(null); // Clear previous results when input changes
  };

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];
    if (selectedFile) {
      clearOtherInputs("file");
      setFile(selectedFile);
      setShowWebcam(false); // Hide webcam if a file is selected
    }
  };

  const activateWebcam = () => {
    clearOtherInputs("webcam");
    setShowWebcam(true);
  };

  const deactivateWebcam = () => {
    setShowWebcam(false);
  };

  const capture = () => {
    if (webcamRef.current) {
      const imgSrc = webcamRef.current.getScreenshot();
      clearOtherInputs("webcam"); // Clear file/name, but keep webcam active for potential re-capture
      setImageSrc(imgSrc);
      // Optionally hide webcam after capture:
      // setShowWebcam(false);
    }
  };

  const handleFullNameChange = (event) => {
    clearOtherInputs("name");
    setFullName(event.target.value);
  };

  const handleImageSubmit = async (event) => {
    event.preventDefault();
    const uploadData = file || imageSrc;

    if (!uploadData) {
      setResult({
        success: false,
        message: "Please select a file or capture an image to upload.",
      });
      return;
    }

    setLoading(true);
    setResult(null);

    let endpoint = "";
    let requestOptions = {};

    if (file) {
      endpoint = `${API_URL}/check-passport-file/`;
      const formData = new FormData();
      formData.append("file", file);
      requestOptions = {
        method: "POST",
        body: formData,
        // 'Content-Type' header is set automatically by the browser for FormData
      };
    } else if (imageSrc) {
      endpoint = `${API_URL}/check-passport-base64/`;
      // react-webcam getScreenshot returns a data URI (e.g., data:image/jpeg;base64,....)
      // We need to send only the base64 part.
      const base64Data = imageSrc.split(",")[1];
      requestOptions = {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ image_data: base64Data }),
      };
    }

    try {
      const response = await fetch(endpoint, requestOptions);
      if (!response.ok) {
        let errorMsg = `Server error: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMsg =
            errorData.message || errorData.detail || JSON.stringify(errorData);
        } catch (e) {
          throw new Error(text || `Server error: ${response.status}`);
        }
        throw new Error(errorMsg);
      }
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error("Error submitting image:", error);
      setResult({
        success: false,
        message: error.message || "Error processing image. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleNameSubmit = async (event) => {
    event.preventDefault();
    if (!fullName.trim()) {
      setResult({
        success: false,
        message: "Please enter a full name to search.",
      });
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await fetch(`${API_URL}/check-name/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ full_name: fullName.trim() }),
      });
      if (!response.ok) {
        let errorMsg = `Server error: ${response.status}`;
        try {
          const errorData = await response.json();
          errorMsg =
            errorData.message || errorData.detail || JSON.stringify(errorData);
        } catch (e) {
          throw new Error(text || `Server error: ${response.status}`);
        }
        throw new Error(errorMsg);
      }
      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error("Error submitting name:", error);
      setResult({
        success: false,
        message: error.message || "Error processing name. Please try again.",
      });
    } finally {
      setLoading(false);
    }
  };

  // --- STYLES ---
  const mainBg = {
    minHeight: "100vh",
    width: "100vw",
    background: "#ecf0f3",
    fontFamily: "'Montserrat', sans-serif",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "flex-start",
    padding: 0,
    margin: 0,
    overflowX: "hidden",
    boxSizing: "border-box",
  };
  const heroSection = {
    width: "100vw",
    minHeight: "100vh",
    maxWidth: "100vw",
    background: "linear-gradient(120deg, #4B70E2 0%, #5a8dee 100%)",
    color: "#fff",
    position: "relative",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    textAlign: "center",
    overflow: "hidden",
    margin: 0,
    padding: 0,
  };
  const heroTitle = {
    fontSize: "3.2rem",
    fontWeight: 800,
    letterSpacing: "-1px",
    marginBottom: 18,
    lineHeight: 1.1,
    zIndex: 2,
  };
  const heroSubtitle = {
    fontSize: "1.35rem",
    fontWeight: 500,
    opacity: 0.97,
    marginBottom: 24,
    letterSpacing: "0.5px",
    zIndex: 2,
  };
  const heroDesc = {
    fontSize: "1.1rem",
    fontWeight: 400,
    maxWidth: 540,
    margin: "0 auto 36px auto",
    color: "#e3eafc",
    zIndex: 2,
  };
  const scrollDownArrow = {
    marginTop: 32,
    zIndex: 2,
    animation: "bounce 1.8s infinite",
    cursor: "pointer",
    display: "inline-block",
  };
  const heroBgImg = {
    position: "absolute",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    objectFit: "cover",
    opacity: 0.18,
    zIndex: 1,
    pointerEvents: "none",
  };
  const formSection = {
    width: "100vw",
    maxWidth: 420,
    margin: "0 auto",
    marginTop: 40,
    background: "#ecf0f3",
    borderRadius: 18,
    boxShadow:
      "8px 8px 24px #d1d9e6, -8px -8px 24px #fff, 0 2px 8px 0 #4B70E220",
    padding: "38px 28px 32px 28px",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    zIndex: 3,
    position: "relative",
    overflow: "hidden",
    boxSizing: "border-box",
  };
  const sectionTitle = {
    fontSize: "1.35rem",
    fontWeight: 700,
    color: "#4B70E2",
    marginBottom: 18,
    letterSpacing: "0.2px",
    textAlign: "center",
  };
  const inputStyle = {
    width: "100%",
    height: 44,
    margin: "8px 0",
    padding: "0 18px",
    fontSize: 15,
    border: "none",
    outline: "none",
    borderRadius: 10,
    background: "#ecf0f3",
    boxShadow: "inset 2px 2px 6px #d1d9e6, inset -2px -2px 6px #fff",
    fontFamily: "'Montserrat', sans-serif",
    transition: "box-shadow 0.2s",
    color: "#2d3748",
  };
  const inputFocusStyle = {
    boxShadow: "inset 4px 4px 8px #d1d9e6, inset -4px -4px 8px #fff",
  };
  const buttonStyle = {
    width: "100%",
    height: 48,
    borderRadius: 24,
    margin: "18px 0 0 0",
    fontWeight: 700,
    fontSize: 16,
    letterSpacing: "0.5px",
    background: "linear-gradient(90deg, #4B70E2 0%, #5a8dee 100%)",
    color: "#fff",
    boxShadow: "4px 4px 12px #d1d9e6, -4px -4px 12px #fff",
    border: "none",
    outline: "none",
    transition: "background 0.2s, box-shadow 0.2s, transform 0.1s",
    cursor: "pointer",
  };
  const buttonDisabled = {
    background: "#b3c6f7",
    color: "#e6eaf6",
    cursor: "not-allowed",
    opacity: 0.7,
  };
  const webcamButton = {
    ...buttonStyle,
    background: "linear-gradient(90deg, #00b4d8 0%, #48cae4 100%)",
    color: "#fff",
  };
  const subtleButton = {
    ...buttonStyle,
    background: "#e3eafc",
    color: "#4B70E2",
    boxShadow: "none",
    border: "1px solid #d1d9e6",
  };
  const separatorStyle = {
    width: "100%",
    display: "flex",
    alignItems: "center",
    margin: "18px 0 18px 0",
  };
  const separatorLine = {
    flex: 1,
    height: 1,
    background: "#d1d9e6",
    border: "none",
  };
  const separatorText = {
    margin: "0 12px",
    color: "#a0a5a8",
    fontWeight: 600,
    fontSize: 13,
    letterSpacing: "0.2px",
  };
  // Webcam button group style
  const webcamButtonGroup = {
    display: "flex",
    flexDirection: "column",
    gap: 12,
    width: "100%",
    alignItems: "center",
    marginTop: 10,
    marginBottom: 0,
  };
  const chooseFileButton = {
    width: "100%",
    borderRadius: 24,
    padding: "12px 0",
    fontWeight: 700,
    fontSize: 17,
    letterSpacing: 0.5,
    background: "linear-gradient(90deg, #2196f3 0%, #1769aa 100%)",
    color: "#fff",
    border: "none",
    outline: "none",
    boxShadow: "0 2px 8px #d1d9e6",
    margin: "18px 0 10px 0",
    cursor: "pointer",
    textAlign: "center",
    transition: "background 0.18s, box-shadow 0.18s, transform 0.1s",
    display: "block",
  };
  const chooseFileButtonHover = {
    background: "linear-gradient(90deg, #1769aa 0%, #1769aa 100%)",
  };

  const linkBoxStyle = {
    marginTop: 12,
    padding: 12,
    borderRadius: 8,
    background: "#fff5f5",
    border: "1.5px solid #ff4d4f",
    color: "#cf1322",
  };

  const linkButtonStyle = {
    ...buttonStyle,
    marginTop: 10,
    background: "linear-gradient(90deg, #ff4d4f 0%, #cf1322 100%)",
    padding: "8px 16px",
    fontSize: "14px",
    height: "auto",
  };

  const linksListStyle = {
    marginTop: 8,
    padding: 8,
    background: "#fff",
    borderRadius: 6,
    border: "1px solid #ffa39e",
    fontSize: "13px",
    color: "#434343",
  };
  // --- END STYLES ---

  return (
    <div style={mainBg}>
      {/* Prevent horizontal scroll and remove body margin */}
      <style>{`
        html, body { overflow-x: hidden; margin: 0; padding: 0; }
        #root { margin: 0; padding: 0; }
        @media (max-width: 600px) {
          .hero-section { padding: 0 !important; }
          .form-section { max-width: 100vw !important; padding: 18px 2vw 18px 2vw !important; border-radius: 0 !important; }
        }
      `}</style>
      {/* Hero Section */}
      <section style={heroSection}>
        {/* Decorative SVG background */}
        <svg
          style={heroBgImg}
          viewBox="0 0 1440 900"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <circle cx="1200" cy="200" r="320" fill="#fff" fillOpacity="0.18" />
          <ellipse
            cx="300"
            cy="700"
            rx="340"
            ry="180"
            fill="#fff"
            fillOpacity="0.13"
          />
          <path
            d="M0 800 Q 600 600 1440 900 V 900 H 0 Z"
            fill="#fff"
            fillOpacity="0.10"
          />
        </svg>
        <h1 style={heroTitle}>Sanctions Compliance Check</h1>
        <p style={heroSubtitle}>
          Instantly check passport images or names for global sanctions
          compliance
        </p>
        <div style={heroDesc}>
          Ensure your business or organization is not dealing with sanctioned
          individuals or entities. Our tool lets you quickly verify names and
          passport images against up-to-date global watchlists, helping you stay
          compliant and avoid regulatory risks.
        </div>
        {/* Scroll Down Arrow */}
        <a
          href="#compliance-form"
          style={scrollDownArrow}
          aria-label="Scroll to form"
        >
          <svg
            width="38"
            height="38"
            viewBox="0 0 38 38"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle cx="19" cy="19" r="19" fill="#fff" fillOpacity="0.18" />
            <path
              d="M12 17l7 7 7-7"
              stroke="#fff"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </a>
        <style>{`
          @keyframes bounce {
            0%, 20%, 50%, 80%, 100% { transform: translateY(0); }
            40% { transform: translateY(10px); }
            60% { transform: translateY(5px); }
          }
        `}</style>
      </section>

      {/* Form Section (below hero, not overlapping) */}
      <div id="compliance-form" style={formSection} className="form-section">
        {/* Passport Image Check */}
        <h2 style={sectionTitle}>Passport Image Check</h2>
        <form onSubmit={handleImageSubmit} style={{ width: "100%" }}>
          <div style={{ marginBottom: 10 }}>
            <label htmlFor="file-upload" style={{ display: "none" }}>
              Upload Passport Image
            </label>
            <label
              htmlFor="file-upload"
              style={chooseFileButton}
              onMouseOver={(e) =>
                Object.assign(e.target.style, chooseFileButtonHover)
              }
              onMouseOut={(e) =>
                Object.assign(e.target.style, chooseFileButton)
              }
            >
              Choose Passport Image
            </label>
            <input
              id="file-upload"
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/*"
              style={{ display: "none" }}
            />
            {file && (
              <p
                style={{
                  marginTop: 8,
                  fontSize: 13,
                  color: "#4B70E2",
                  textAlign: "center",
                }}
              >
                Selected: <span style={{ fontWeight: 600 }}>{file.name}</span>
              </p>
            )}
          </div>

          {/* Separator for webcam */}
          <div style={separatorStyle}>
            <hr style={separatorLine} />
            <span style={separatorText}>OR USE WEBCAM</span>
            <hr style={separatorLine} />
          </div>

          {!showWebcam && (
            <button type="button" onClick={activateWebcam} style={webcamButton}>
              Activate Camera
            </button>
          )}

          {showWebcam && (
            <div
              style={{
                border: "1.5px solid #d1d9e6",
                padding: 18,
                borderRadius: 12,
                background: "#f9f9f9",
                margin: "18px 0 0 0",
                boxShadow: "0 2px 8px #d1d9e6",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                width: "100%",
              }}
            >
              <Webcam
                audio={false}
                ref={webcamRef}
                screenshotFormat="image/jpeg"
                width={260}
                height={180}
                videoConstraints={{ facingMode: "user" }}
                style={{
                  borderRadius: 8,
                  border: "2px solid #4B70E2",
                  marginBottom: 10,
                }}
              />
              <div style={webcamButtonGroup}>
                <button
                  type="button"
                  onClick={capture}
                  style={{
                    ...webcamButton,
                    width: "100%",
                    margin: 0,
                    fontSize: 17,
                    letterSpacing: 0.5,
                  }}
                >
                  Capture from Webcam
                </button>
                <button
                  type="button"
                  onClick={deactivateWebcam}
                  style={{
                    ...subtleButton,
                    width: "100%",
                    margin: 0,
                    fontSize: 17,
                    letterSpacing: 0.5,
                    background: "#e3eafc",
                    color: "#4B70E2",
                    border: "1.5px solid #b3c6f7",
                    boxShadow: "none",
                  }}
                >
                  Deactivate Camera
                </button>
              </div>
            </div>
          )}

          {imageSrc && (
            <div
              style={{
                marginTop: 18,
                textAlign: "center",
                padding: 12,
                background: "#f9f9f9",
                borderRadius: 10,
                border: "1.5px solid #d1d9e6",
                boxShadow: "0 2px 8px #d1d9e6",
              }}
            >
              <h3
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: "#4B70E2",
                  marginBottom: 8,
                }}
              >
                Image Preview:
              </h3>
              <img
                src={imageSrc}
                alt="Captured"
                style={{
                  width: 180,
                  height: 120,
                  objectFit: "cover",
                  borderRadius: 8,
                  border: "2px solid #4B70E2",
                }}
              />
            </div>
          )}

          <button
            type="submit"
            disabled={loading || (!file && !imageSrc)}
            style={{
              ...buttonStyle,
              marginTop: 22,
              ...(loading || (!file && !imageSrc) ? buttonDisabled : {}),
            }}
          >
            {loading && (file || imageSrc) ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg
                  className="animate-spin"
                  style={{ marginRight: 8, width: 20, height: 20 }}
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Processing Image...
              </div>
            ) : (
              "Check Passport Image"
            )}
          </button>
        </form>

        {/* Separator for Name Check */}
        <div style={separatorStyle}>
          <hr style={separatorLine} />
          <span style={separatorText}>OR</span>
          <hr style={separatorLine} />
        </div>

        {/* Name Check Section */}
        <h2 style={sectionTitle}>Name Check</h2>
        <form onSubmit={handleNameSubmit} style={{ width: "100%" }}>
          <div style={{ marginBottom: 8 }}>
            <label
              htmlFor="full-name"
              style={{
                display: "block",
                fontSize: 14,
                fontWeight: 600,
                color: "#4B70E2",
                marginBottom: 6,
              }}
            >
              Full Name
            </label>
            <input
              id="full-name"
              type="text"
              value={fullName}
              onChange={handleFullNameChange}
              placeholder="Enter full name for sanctions check"
              style={inputStyle}
              onFocus={(e) =>
                (e.target.style.boxShadow = inputFocusStyle.boxShadow)
              }
              onBlur={(e) => (e.target.style.boxShadow = inputStyle.boxShadow)}
            />
          </div>
          <button
            type="submit"
            disabled={loading || !fullName.trim()}
            style={{
              ...buttonStyle,
              marginTop: 12,
              ...(loading || !fullName.trim() ? buttonDisabled : {}),
            }}
          >
            {loading && fullName ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <svg
                  className="animate-spin"
                  style={{ marginRight: 8, width: 20, height: 20 }}
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Processing Name...
              </div>
            ) : (
              "Check Name"
            )}
          </button>
        </form>

        {/* Result Display (common for all types of checks) */}
        {result && (
          <div
            style={{
              marginTop: 28,
              padding: 18,
              borderRadius: 12,
              boxShadow: "0 2px 8px #d1d9e6",
              width: "100%",
              background: result.success ? "#e6f9f0" : "#ffeaea",
              border: result.success
                ? "1.5px solid #4B70E2"
                : "1.5px solid #e53935",
              textAlign: "center",
            }}
          >
            {!result.success && (
              <div style={{ color: "#e53935" }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>
                  Error
                </h2>
                <p style={{ fontSize: 15 }}>
                  {result.message || "An unknown error occurred."}
                </p>
              </div>
            )}
            {result.success && (
              <div style={{ color: "#388e3c" }}>
                <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>
                  Processing Result
                </h2>
                <p style={{ fontSize: 15 }}>{result.message}</p>
                {result.match_found !== false && (
                  <div
                    style={{
                      marginTop: 14,
                      paddingTop: 10,
                      borderTop: "1px solid #b2dfdb",
                    }}
                  >
                    <h3
                      style={{
                        fontSize: 15,
                        fontWeight: 600,
                        color: "#388e3c",
                        marginBottom: 6,
                      }}
                    >
                      Match Details:
                    </h3>
                    <div
                      style={{
                        fontSize: 13,
                        background: "#fff",
                        padding: 10,
                        borderRadius: 8,
                        border: "1px solid #b2dfdb",
                        boxShadow: "0 1px 4px #d1d9e6",
                      }}
                    >
                      {Object.entries(result.match_details).map(([key, value]) => {
                        // Skip rendering the links field here
                        if (key === "links") return null;

                        return (
                          <p
                            key={key}
                            style={{
                              color: "#333",
                              margin: 0,
                              textAlign: "left",
                            }}
                          >
                            <span
                              style={{
                                fontWeight: 600,
                                color: "#4B70E2",
                                textTransform: "capitalize",
                              }}
                            >
                              {key.replace(/_/g, " ")}:{" "}
                            </span>
                            {Array.isArray(value) ? value.join(", ") : String(value)}
                          </p>
                        );
                      })}
                    </div>

                    {/* Links Display Section */}
                    {result.match_details?.links && (
                      <div style={linkBoxStyle}>
                        <p style={{ margin: 0, fontWeight: 600 }}>
                          The name was flagged for suspicious activities
                        </p>
                        <button
                          onClick={() => setShowLinks(!showLinks)}
                          style={linkButtonStyle}
                        >
                          {showLinks ? "Hide Details" : "Show Details"}
                        </button>
                        {showLinks && (
                          <div style={linksListStyle}>
                            <ul style={{ margin: 0, paddingLeft: 20 }}>
                              {result.match_details.links.map((link, index) => (
                                <li key={index} style={{ marginBottom: 4 }}>
                                  <a
                                    href={link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    style={{ color: "#1890ff" }}
                                  >
                                    {link}
                                  </a>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
                {result.match_found === false && (
                  <p style={{ color: "#388e3c", marginTop: 10 }}>
                    No matches found!
                  </p>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default FileUpload;
