/**
 * CameraStreamController:
 * Captures live webcam feed or synthetic classroom simulator,
 * posts frames to /api/process_frame, and renders annotated vision HUD.
 */
class CameraStreamController {
  constructor() {
    this.videoElement = document.createElement('video');
    this.videoElement.autoplay = true;
    this.videoElement.muted = true;
    this.videoElement.playsInline = true;

    this.canvas = document.createElement('canvas');
    this.ctx = this.canvas.getContext('2d');
    this.annotatedImg = document.getElementById('annotatedImage');
    this.hudText = document.getElementById('cameraHudText');
    
    this.isRunning = false;
    this.isProcessing = false;
    this.stream = null;
    this.simulationMode = false;
    this.fps = 8;
    this.intervalId = null;

    // Simulation animation state
    this.simulatedAngle = 0;
  }

  async startWebcam() {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false
      });
      this.videoElement.srcObject = this.stream;
      await this.videoElement.play();
      this.simulationMode = false;
      this.hudText.innerText = "LIVE WEBCAM STREAMING (640x480)";
      this._startCaptureLoop();
    } catch (err) {
      console.warn("[CameraStream] Physical webcam inaccessible or denied, falling back to Classroom Simulator:", err);
      this.startSimulator();
    }
  }

  startSimulator() {
    this.simulationMode = true;
    this.hudText.innerText = "VIRTUAL CLASSROOM SIMULATOR ACTIVE";
    this._startCaptureLoop();
  }

  stop() {
    this.isRunning = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    this.hudText.innerText = "STREAM PAUSED";
  }

  _startCaptureLoop() {
    this.isRunning = true;
    this.intervalId = setInterval(() => this._captureAndSend(), 1000 / this.fps);
  }

  async _captureAndSend() {
    if (!this.isRunning || this.isProcessing) return;

    let frameB64 = "";
    if (!this.simulationMode && this.videoElement.videoWidth > 0) {
      this.canvas.width = 640;
      this.canvas.height = 480;
      this.ctx.drawImage(this.videoElement, 0, 0, 640, 480);
      frameB64 = this.canvas.toDataURL('image/jpeg', 0.7);
    } else {
      // Draw realistic simulated student classroom scene
      frameB64 = this._generateSimulatedFrame();
    }

    this.isProcessing = true;
    try {
      const audioRms = window.audioRecorder ? window.audioRecorder.getCurrentRMS() : 0.03;

      const response = await fetch('/api/process_frame', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image: frameB64,
          client_audio_rms: audioRms
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.annotated_frame) {
          this.annotatedImg.src = data.annotated_frame;
        }
        if (window.appController) {
          window.appController.updateTelemetry(data);
        }
      }
    } catch (err) {
      console.error("[CameraStream] Process frame error:", err);
    } finally {
      this.isProcessing = false;
    }
  }

  _generateSimulatedFrame() {
    this.canvas.width = 640;
    this.canvas.height = 480;
    const ctx = this.ctx;

    // Background Classroom Setting
    ctx.fillStyle = "#1e293b";
    ctx.fillRect(0, 0, 640, 480);

    // Chalkboard / Presentation Screen in background
    ctx.fillStyle = "#0f172a";
    ctx.fillRect(40, 30, 560, 160);
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 4;
    ctx.strokeRect(40, 30, 560, 160);

    ctx.fillStyle = "#38bdf8";
    ctx.font = "bold 16px sans-serif";
    ctx.fillText("LECTURE TOPIC: Deep Learning & Multimodal Attention", 70, 75);
    ctx.fillStyle = "#94a3b8";
    ctx.font = "14px monospace";
    ctx.fillText("Formula: E(t) = w_v * V_attn(t) + w_m * V_mot(t) + w_a * A_int(t)", 70, 115);
    ctx.fillText("Status: Sustained Attendance Verification Active", 70, 145);

    // Dynamic simulated student faces
    this.simulatedAngle += 0.05;
    const wobble1 = Math.sin(this.simulatedAngle) * 8;
    const wobble2 = Math.cos(this.simulatedAngle * 0.8) * 6;

    // Student 1 (Desk Left)
    this._drawSimulatedStudent(ctx, 160 + wobble1, 310 + wobble2, "STD-101", "#fbcfe8");
    // Student 2 (Desk Center)
    this._drawSimulatedStudent(ctx, 330, 300 - wobble1 * 0.5, "STD-102", "#fed7aa");
    // Student 3 (Desk Right)
    this._drawSimulatedStudent(ctx, 490 - wobble2, 315 + wobble1 * 0.5, "STD-103", "#fef08a");

    return this.canvas.toDataURL('image/jpeg', 0.8);
  }

  _drawSimulatedStudent(ctx, x, y, label, skinColor) {
    // Body / Shoulders
    ctx.fillStyle = "#334155";
    ctx.beginPath();
    ctx.ellipse(x, y + 90, 70, 45, 0, 0, Math.PI * 2);
    ctx.fill();

    // Head / Face
    ctx.fillStyle = skinColor;
    ctx.beginPath();
    ctx.arc(x, y, 42, 0, Math.PI * 2);
    ctx.fill();

    // Hair
    ctx.fillStyle = "#1e1e24";
    ctx.beginPath();
    ctx.arc(x, y - 10, 43, Math.PI, Math.PI * 2);
    ctx.fill();

    // Eyes
    ctx.fillStyle = "#0f172a";
    ctx.beginPath();
    ctx.arc(x - 14, y - 2, 4, 0, Math.PI * 2);
    ctx.arc(x + 14, y - 2, 4, 0, Math.PI * 2);
    ctx.fill();

    // Smile / Expression
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(x, y + 12, 10, 0.2, Math.PI - 0.2);
    ctx.stroke();
  }
}

window.CameraStreamController = CameraStreamController;
