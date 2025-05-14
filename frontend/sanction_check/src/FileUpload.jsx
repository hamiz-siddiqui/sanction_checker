// src/FileUpload.jsx
import React, { useState, useRef } from 'react';
import Webcam from 'react-webcam';
import './App.css'

const API_URL = import.meta.env.VITE_API_URL
console.log("API_URL:", API_URL);

const FileUpload = () => {
    const [file, setFile] = useState(null);
    const [imageSrc, setImageSrc] = useState(null);
    const [fullName, setFullName] = useState('');

    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [showWebcam, setShowWebcam] = useState(false);

    const webcamRef = useRef(null);
    const fileInputRef = useRef(null);

    const clearOtherInputs = (inputType) => {
        if (inputType !== 'file') {
            setFile(null);
            if (fileInputRef.current) fileInputRef.current.value = "";
        }
        if (inputType !== 'webcam') {
            setImageSrc(null);
            // Optionally hide webcam if another input is used
            // setShowWebcam(false);
        }
        if (inputType !== 'name') {
            setFullName('');
        }
        setResult(null); // Clear previous results when input changes
    };

    const handleFileChange = (event) => {
        const selectedFile = event.target.files[0];
        if (selectedFile) {
            clearOtherInputs('file');
            setFile(selectedFile);
            setShowWebcam(false); // Hide webcam if a file is selected
        }
    };

    const activateWebcam = () => {
        clearOtherInputs('webcam');
        setShowWebcam(true);
    };

    const deactivateWebcam = () => {
        setShowWebcam(false);
    };

    const capture = () => {
        if (webcamRef.current) {
            const imgSrc = webcamRef.current.getScreenshot();
            clearOtherInputs('webcam'); // Clear file/name, but keep webcam active for potential re-capture
            setImageSrc(imgSrc);
            // Optionally hide webcam after capture:
            // setShowWebcam(false);
        }
    };

    const handleFullNameChange = (event) => {
        clearOtherInputs('name');
        setFullName(event.target.value);
    };

    const handleImageSubmit = async (event) => {
        event.preventDefault();
        const uploadData = file || imageSrc;

        if (!uploadData) {
            setResult({ success: false, message: 'Please select a file or capture an image to upload.' });
            return;
        }

        setLoading(true);
        setResult(null);

        let endpoint = '';
        let requestOptions = {};

        if (file) {
            endpoint = `${API_URL}/check-passport-file/`;
            const formData = new FormData();
            formData.append('file', file);
            requestOptions = {
                method: 'POST',
                body: formData,
                // 'Content-Type' header is set automatically by the browser for FormData
            };
        } else if (imageSrc) {
            endpoint = `${API_URL}/check-passport-base64/`;
            // react-webcam getScreenshot returns a data URI (e.g., data:image/jpeg;base64,....)
            // We need to send only the base64 part.
            const base64Data = imageSrc.split(',')[1];
            requestOptions = {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
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
                    errorMsg = errorData.message || errorData.detail || JSON.stringify(errorData);
                } catch (e) {
                    throw new Error(text || `Server error: ${response.status}`);
                }
                throw new Error(errorMsg);
            }
            const data = await response.json();
            setResult(data);
        } catch (error) {
            console.error('Error submitting image:', error);
            setResult({ success: false, message: error.message || 'Error processing image. Please try again.' });
        } finally {
            setLoading(false);
        }
    };

    const handleNameSubmit = async (event) => {
        event.preventDefault();
        if (!fullName.trim()) {
            setResult({ success: false, message: 'Please enter a full name to search.' });
            return;
        }

        setLoading(true);
        setResult(null);

        try {
            const response = await fetch(`${API_URL}/check-name/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ full_name: fullName.trim() }),
            });
            if (!response.ok) {
                let errorMsg = `Server error: ${response.status}`;
                try {
                    const errorData = await response.json();
                    errorMsg = errorData.message || errorData.detail || JSON.stringify(errorData);
                } catch (e) {
                    throw new Error(text || `Server error: ${response.status}`);
                }
                throw new Error(errorMsg);
            }
            const data = await response.json();
            setResult(data);
        } catch (error) {
            console.error('Error submitting name:', error);
            setResult({ success: false, message: error.message || 'Error processing name. Please try again.' });
        } finally {
            setLoading(false);
        }
    };


    const baseButtonClass = "w-full font-semibold py-2.5 px-4 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-opacity-75 transition-all duration-150 ease-in-out";
    const primaryButtonClass = `${baseButtonClass} bg-indigo-600 hover:bg-indigo-700 text-white focus:ring-indigo-500`;
    const secondaryButtonClass = `${baseButtonClass} bg-sky-500 hover:bg-sky-600 text-white focus:ring-sky-400`;
    const tertiaryButtonClass = `${baseButtonClass} bg-emerald-500 hover:bg-emerald-600 text-white focus:ring-emerald-400`;
    const subtleButtonClass = `${baseButtonClass} bg-slate-200 hover:bg-slate-300 text-slate-700 focus:ring-slate-400`;
    const disabledButtonClass = "bg-slate-300 text-slate-500 cursor-not-allowed opacity-70";

    const Separator = () => (
        <div className="relative flex items-center py-4">
            <div className="flex-grow border-t border-slate-300"></div>
            <span className="flex-shrink mx-4 text-slate-400 font-medium text-sm">OR</span>
            <div className="flex-grow border-t border-slate-300"></div>
        </div>
    );

    return (
        <div className="min-h-screen bg-slate-100 flex flex-col items-center justify-center p-4 selection:bg-indigo-100 selection:text-indigo-700">
            <div className="bg-white p-6 sm:p-8 rounded-xl shadow-2xl w-full max-w-lg space-y-6">
                <h1 className="text-3xl sm:text-4xl font-bold text-center text-indigo-600">
                    Sanctions Compliance Check
                </h1>

                {/* --- Passport Image Check Section --- */}
                <section>
                    <h2 className="text-xl font-semibold text-slate-700 mb-4 text-center">Passport Image Check</h2>
                    <form onSubmit={handleImageSubmit} className="space-y-6 w-full">
                        <div>
                            <label htmlFor="file-upload" className="sr-only">Upload Passport Image</label>
                            <label
                                htmlFor="file-upload"
                                className={`${secondaryButtonClass} text-center cursor-pointer block hover:shadow-md`}
                            >
                                Choose Passport Image
                            </label>
                            <input
                                id="file-upload"
                                type="file"
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                accept="image/*"
                                className="hidden"
                            />
                            {file && (
                                <p className="mt-2 text-sm text-slate-600 text-center">
                                    Selected: <span className="font-medium text-slate-700">{file.name}</span>
                                </p>
                            )}
                        </div>

                        <div className="relative flex items-center py-2">
                           <div className="flex-grow border-t border-slate-300"></div>
                           <span className="flex-shrink mx-4 text-slate-400 font-medium text-xs">OR USE WEBCAM</span>
                           <div className="flex-grow border-t border-slate-300"></div>
                        </div>


                        {!showWebcam && (
                            <button
                                type="button"
                                onClick={activateWebcam}
                                className={`${tertiaryButtonClass} hover:shadow-md`}
                            >
                                Activate Camera
                            </button>
                        )}

                        {showWebcam && (
                            <div className="border border-slate-200 p-4 rounded-lg bg-slate-50 space-y-4 flex flex-col items-center shadow">
                                <Webcam
                                    audio={false}
                                    ref={webcamRef}
                                    screenshotFormat="image/jpeg" // For base64, jpeg or png is fine
                                    width={300}
                                    height={225}
                                    videoConstraints={{ facingMode: "user" }}
                                    className="rounded-md border-2 border-slate-300"
                                />
                                <button
                                    type="button"
                                    onClick={capture}
                                    className={`${secondaryButtonClass.replace('w-full','')} max-w-xs hover:shadow-md`}
                                >
                                    Capture from Webcam
                                </button>
                                <button
                                    type="button"
                                    onClick={deactivateWebcam}
                                    className={`${subtleButtonClass.replace('w-full','')} max-w-xs hover:shadow-md`}
                                >
                                    Deactivate Camera
                                </button>
                            </div>
                        )}

                        {imageSrc && (
                            <div className="mt-4 text-center p-4 bg-slate-50 rounded-lg border border-slate-200 shadow">
                                <h3 className="text-lg font-semibold mb-3 text-slate-700">Image Preview:</h3>
                                <img
                                    src={imageSrc}
                                    alt="Captured"
                                    className="mx-auto rounded-md border-2 border-slate-300"
                                    style={{ width: '240px', height: '180px', objectFit: 'cover' }}
                                />
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={loading || (!file && !imageSrc)}
                            className={`${primaryButtonClass} ${(loading || (!file && !imageSrc)) ? disabledButtonClass : 'hover:shadow-lg hover:bg-indigo-700'}`}
                        >
                            {loading && (file || imageSrc) ? (
                                <div className="flex items-center justify-center">
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Processing Image...
                                </div>
                            ) : 'Check Passport Image'}
                        </button>
                    </form>
                </section>

                <Separator />

                {/* --- Name Check Section --- */}
                <section>
                    <h2 className="text-xl font-semibold text-slate-700 mb-4 text-center">Name Check</h2>
                    <form onSubmit={handleNameSubmit} className="space-y-4 w-full">
                        <div>
                            <label htmlFor="full-name" className="block text-sm font-medium text-slate-700 mb-1">
                                Full Name
                            </label>
                            <input
                                id="full-name"
                                type="text"
                                value={fullName}
                                onChange={handleFullNameChange}
                                placeholder="Enter full name for sanctions check"
                                className="mt-1 block w-full px-3 py-2 bg-white border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={loading || !fullName.trim()}
                            className={`${primaryButtonClass} ${(loading || !fullName.trim()) ? disabledButtonClass : 'hover:shadow-lg hover:bg-indigo-700'}`}
                        >
                            {loading && fullName ? (
                                 <div className="flex items-center justify-center">
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Processing Name...
                                </div>
                            ) : 'Check Name'}
                        </button>
                    </form>
                </section>


                {/* Result Display (common for all types of checks) */}
                {result && (
                    <div className={`mt-8 p-5 rounded-lg shadow w-full text-base ${result.success ? 'border border-green-300 bg-green-50' : 'border border-red-300 bg-red-50'} text-center`}>
                        {!result.success && (
                            <div className="text-red-700 space-y-1">
                                <h2 className="text-xl font-semibold text-red-800">Error</h2>
                                <p className="text-red-600">{result.message || 'An unknown error occurred.'}</p>
                            </div>
                        )}
                        {result.success && (
                            <div className="text-green-700 space-y-2">
                                <h2 className="text-xl font-semibold text-green-800">Processing Result</h2>
                                <p className="text-green-600">{result.message}</p>
                                {result.match_found !== false && (
                                    <div className="mt-4 pt-4 border-t border-green-200">
                                        <h3 className="text-lg font-semibold text-green-700 mb-2">Match Details:</h3>
                                        <div className="space-y-1.5 text-sm bg-white p-4 rounded-md border border-green-200 shadow-sm">
                                            {Object.entries(result.match_details).map(([key, value]) => (
                                                <p key={key} className="text-slate-700">
                                                    <span className="font-semibold text-slate-800 capitalize">{key.replace(/_/g, ' ')}:</span> {String(value)}
                                                </p>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {result.match_found === false && (
                                        <p className="text-green-600">No matches found!</p>
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