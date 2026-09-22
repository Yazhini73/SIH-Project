const form = document.querySelector('#scan-form');
const message = document.querySelector('#scan-message');
const cameraMessage = document.querySelector('#camera-message');
const video = document.querySelector('#camera');
const canvas = document.querySelector('#snapshot');
const placeholder = document.querySelector('#camera-placeholder');
const capturedPreview = document.querySelector('#captured-preview');
const uploadPreview = document.querySelector('#upload-preview');
const currentImage = document.querySelector('#current-image');
const capture = document.querySelector('#capture');
const retake = document.querySelector('#retake');
const useCameraImage = document.querySelector('#use-camera-image');
const uploadInput = document.querySelector('#strip-image');
let cameraStream;
let scanImage = null;
let inputMethod = null;
let pendingCameraImage = null;

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = undefined;
  }
  video.srcObject = null;
  capture.disabled = true;
}

function setCurrentImage(file, method) {
  scanImage = file;
  inputMethod = method;
  currentImage.textContent = `Current scan image: ${method === 'camera' ? 'Camera' : 'Upload'}`;
  if (method === 'upload') {
    uploadPreview.src = URL.createObjectURL(file);
    uploadPreview.hidden = false;
  } else {
    uploadPreview.hidden = true;
  }
}

document.querySelector('#start-camera').addEventListener('click', async () => {
  if (!navigator.mediaDevices?.getUserMedia) {
    cameraMessage.textContent = 'Live camera is not available on this device/browser. Please use Upload Image instead.';
    return;
  }
  stopCamera();
  cameraMessage.textContent = '';
  try {
    cameraStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    video.srcObject = cameraStream;
    video.muted = true;
    await video.play();
    video.hidden = false;
    placeholder.hidden = true;
    capturedPreview.hidden = true;
    capture.disabled = false;
    capture.hidden = false;
    retake.hidden = true;
    useCameraImage.hidden = true;
  } catch (error) {
    const errors = {
      NotAllowedError: 'Camera access was denied. Please allow camera permission in your browser settings or use Upload Image instead.',
      NotFoundError: 'No webcam was found. Please connect a webcam or use Upload Image instead.',
      NotReadableError: 'The webcam is already being used by another application. Close it there and try again.',
      SecurityError: 'Browser security prevents camera access. Open this app through its local web address and allow camera permission.',
      TypeError: 'The camera request was invalid. Please use Upload Image instead.'
    };
    cameraMessage.textContent = errors[error.name] || 'The webcam could not be started. Please use Upload Image instead.';
  }
});

capture.addEventListener('click', () => {
  if (!video.videoWidth || !video.videoHeight) {
    cameraMessage.textContent = 'The camera preview is not ready. Please try again.';
    return;
  }
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob((blob) => {
    pendingCameraImage = new File([blob], 'camera-capture.jpg', { type: 'image/jpeg' });
    capturedPreview.src = URL.createObjectURL(pendingCameraImage);
    capturedPreview.hidden = false;
    useCameraImage.hidden = false;
  }, 'image/jpeg', 0.92);
  stopCamera();
  video.hidden = true;
  capture.hidden = true;
  retake.hidden = false;
  cameraMessage.textContent = 'Captured image ready. Review it, then choose Use This Image.';
});

retake.addEventListener('click', () => {
  pendingCameraImage = null;
  capturedPreview.hidden = true;
  useCameraImage.hidden = true;
  retake.hidden = true;
  cameraMessage.textContent = '';
  document.querySelector('#start-camera').click();
});

useCameraImage.addEventListener('click', () => {
  if (!pendingCameraImage) return;
  setCurrentImage(pendingCameraImage, 'camera');
  useCameraImage.hidden = true;
  cameraMessage.textContent = 'Camera image selected. Enter moisture and analyze.';
});

uploadInput.addEventListener('change', () => {
  const file = uploadInput.files[0];
  if (!file) return;
  stopCamera();
  pendingCameraImage = null;
  capturedPreview.hidden = true;
  useCameraImage.hidden = true;
  retake.hidden = true;
  setCurrentImage(file, 'upload');
  cameraMessage.textContent = '';
  message.textContent = 'Upload image selected. Enter moisture and analyze.';
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!scanImage) { message.textContent = 'Choose an image or capture the complete strip with Live Camera.'; return; }
  const moistureValue = form.elements.moisture.value.trim();
  if (!moistureValue) { message.textContent = 'Please enter the moisture percentage.'; return; }
  if (!Number.isFinite(Number(moistureValue)) || Number(moistureValue) < 0) { message.textContent = 'Please enter a valid moisture percentage.'; return; }
  message.textContent = 'Validating the complete strip...';
  const data = new FormData();
  data.append('image', scanImage, scanImage.name || 'strip-image.jpg');
  data.append('moisture', moistureValue);
  data.append('input_method', inputMethod);
  try {
    const response = await fetch('/api/analyze', { method: 'POST', body: data });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Analysis failed.');
    sessionStorage.setItem('feedsenseResults', JSON.stringify(payload));
    window.location.href = '/results';
  } catch (error) {
    message.textContent = error.message;
  }
});

window.addEventListener('pagehide', stopCamera);
