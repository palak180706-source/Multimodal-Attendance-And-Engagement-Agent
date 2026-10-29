/**
 * Main Application Controller for Multimodal Attendance & Engagement Agent
 */
class AppController {
  constructor() {
    this.camera = null;
    this.audio = null;
    this.charts = null;
    this.audioPlayer = new Audio();
    this.init();
  }

  init() {
    this.camera = new CameraStreamController();
    this.audio = new AudioRecorderController();
    this.charts = new EngagementChartsController();

    window.cameraStream = this.camera;
    window.audioRecorder = this.audio;
    window.engagementCharts = this.charts;

    this.bindEvents();
    this.startSystem();
  }

  async startSystem() {
    await this.audio.start();
    await this.camera.startWebcam();
  }

  bindEvents() {
    // Session Controls
    const btnStop = document.getElementById('btnStopSession');
    const btnStart = document.getElementById('btnStartSession');
    const btnTriggerAi = document.getElementById('btnTriggerAi');
    const btnGenerateQuiz = document.getElementById('btnGenerateQuiz');
    const btnToggleSim = document.getElementById('btnToggleSimulator');
    const btnExportCsv = document.getElementById('btnExportCsv');

    if (btnStop) {
      btnStop.addEventListener('click', () => this.stopSession());
    }
    if (btnStart) {
      btnStart.addEventListener('click', () => this.startSession());
    }
    if (btnTriggerAi) {
      btnTriggerAi.addEventListener('click', () => this.requestManualAiAdvice());
    }
    if (btnGenerateQuiz) {
      btnGenerateQuiz.addEventListener('click', () => this.generateInteractiveQuiz());
    }
    if (btnToggleSim) {
      btnToggleSim.addEventListener('click', () => {
        if (this.camera.simulationMode) {
          this.camera.startWebcam();
        } else {
          this.camera.startSimulator();
        }
      });
    }
    if (btnExportCsv) {
      btnExportCsv.addEventListener('click', () => {
        window.location.href = '/api/attendance/export';
      });
    }
  }

  updateTelemetry(data) {
    const fused = data.fused_telemetry;
    const students = data.students || [];

    // 1. Update Top Metrics
    const metricFused = document.getElementById('metricFusedScore');
    const badgeCategory = document.getElementById('badgeCategory');
    const metricPresent = document.getElementById('metricPresentStudents');
    const metricAcoustic = document.getElementById('metricAcousticState');
    const metricAttention = document.getElementById('metricVisualAttention');

    if (metricFused) metricFused.innerText = `${fused.fused_score}%`;
    if (badgeCategory) {
      badgeCategory.innerText = fused.category_label;
      badgeCategory.className = `metric-badge badge-${fused.badge_color}`;
    }
    if (metricPresent) metricPresent.innerText = `${fused.present_students} / ${fused.active_faces}`;
    if (metricAcoustic) metricAcoustic.innerText = fused.acoustic_state.replace(/_/g, ' ');
    if (metricAttention) metricAttention.innerText = `${fused.visual_attention}%`;

    // 2. Stream to Charts
    if (this.charts) {
      this.charts.addSnapshot(fused);
    }

    // 3. Update Attendance Table
    this.renderAttendanceTable(students);

    // 4. Handle Alerts
    if (fused.alert) {
      this.displayAlertBanner(fused.alert);
    }

    // 5. Handle AI Suggestions
    if (data.ai_suggestion) {
      this.renderAiSuggestion(data.ai_suggestion);
    }
  }

  renderAttendanceTable(students) {
    const tbody = document.getElementById('attendanceTableBody');
    if (!tbody) return;

    if (students.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: #94a3b8; padding: 2rem;">No participants currently detected in camera frame.</td></tr>`;
      return;
    }

    let rowsHtml = '';
    students.forEach(st => {
      const isPresent = st.status === 'PRESENT';
      const statusBadge = isPresent
        ? `<span class="status-badge" style="background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3);">✔ PRESENT</span>`
        : `<span class="status-badge" style="background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3);">⏳ VERIFYING (${st.sustained_duration}s)</span>`;

      rowsHtml += `
        <tr>
          <td style="font-weight: 600; color: #cbd5e1;">${st.student_id}</td>
          <td><strong>${st.name}</strong></td>
          <td>${statusBadge}</td>
          <td><span style="color: ${st.attention_score >= 65 ? '#34d399' : '#f87171'}; font-weight: 700;">${st.attention_score}%</span></td>
          <td><span style="font-size: 0.8rem; color: #94a3b8;">${st.head_pose}</span></td>
          <td>${st.sustained_duration}s</td>
        </tr>
      `;
    });

    tbody.innerHTML = rowsHtml;
  }

  displayAlertBanner(alert) {
    const banner = document.getElementById('systemAlertBanner');
    if (!banner) return;

    banner.style.display = 'flex';
    banner.innerText = alert.message;
    if (alert.severity === 'WARNING') {
      banner.style.background = 'rgba(239, 68, 68, 0.2)';
      banner.style.border = '1px solid rgba(239, 68, 68, 0.4)';
      banner.style.color = '#fca5a5';
    } else {
      banner.style.background = 'rgba(16, 185, 129, 0.2)';
      banner.style.border = '1px solid rgba(16, 185, 129, 0.4)';
      banner.style.color = '#86efac';
    }

    setTimeout(() => {
      banner.style.display = 'none';
    }, 6000);
  }

  renderAiSuggestion(ai) {
    const container = document.getElementById('aiSuggestionBox');
    if (!container) return;

    container.innerHTML = `
      <div class="ai-rec-header">
        <span class="metric-badge badge-blue">${ai.category}</span>
        <span style="font-size: 0.75rem; color: #94a3b8;">Priority: <strong style="color: #f59e0b;">${ai.priority}</strong></span>
      </div>
      <p style="font-size: 0.92rem; line-height: 1.45; color: #f1f5f9; margin-top: 0.35rem;">
        ${ai.suggestion}
      </p>
      ${ai.suggested_prompt ? `<div class="ai-prompt-box">💬 Teacher Prompt: "${ai.suggested_prompt}"</div>` : ''}
      <div style="margin-top: 0.85rem; display: flex; gap: 0.5rem;">
        ${ai.audio_file ? `<button class="btn btn-secondary" onclick="appController.playAudio('${ai.audio_file}')">🔊 Hear Audio Prompt</button>` : ''}
        <button class="btn btn-primary" onclick="appController.generateInteractiveQuiz()">🎯 Launch Concept Poll</button>
      </div>
    `;
  }

  playAudio(filename) {
    this.audioPlayer.src = `/audio/${filename}`;
    this.audioPlayer.play().catch(e => console.log("Audio autoplay prevented:", e));
  }

  async requestManualAiAdvice() {
    try {
      const resp = await fetch('/api/trigger_suggestion', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Instructor Prompt Request' })
      });
      const data = await resp.json();
      if (data.suggestion) {
        this.renderAiSuggestion(data.suggestion);
      }
    } catch (e) {
      console.error(e);
    }
  }

  async generateInteractiveQuiz() {
    try {
      const resp = await fetch('/api/generate_quiz', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: 'Deep Learning & Multimodal Attendance' })
      });
      const data = await resp.json();
      if (data.quiz) {
        this.showQuizModal(data.quiz);
      }
    } catch (e) {
      console.error(e);
    }
  }

  showQuizModal(quiz) {
    const modal = document.getElementById('quizModal');
    const content = document.getElementById('quizModalContent');
    if (!modal || !content) return;

    content.innerHTML = `
      <h3 style="margin-bottom: 0.75rem; color: #818cf8;">Instant Concept Check</h3>
      <p style="font-weight: 600; font-size: 1rem; margin-bottom: 1rem;">${quiz.question}</p>
      <div style="display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem;">
        ${quiz.options.map(opt => `<button class="btn btn-secondary" style="justify-content: flex-start; text-align: left;" onclick="alert('Response Recorded! Optimal Answer: ${quiz.correct_option}')">${opt}</button>`).join('')}
      </div>
      <p style="font-size: 0.82rem; color: #94a3b8; font-style: italic;">${quiz.explanation}</p>
      <div style="margin-top: 1rem; text-align: right;">
        <button class="btn btn-primary" onclick="document.getElementById('quizModal').style.display='none'">Close Poll</button>
      </div>
    `;
    modal.style.display = 'flex';
  }

  async stopSession() {
    if (!confirm("Are you sure you want to conclude the current session?")) return;
    try {
      const resp = await fetch('/api/session/stop', { method: 'POST' });
      const data = await resp.json();
      alert(`Session Concluded!\n${data.summary}`);
      this.camera.stop();
      window.location.reload();
    } catch (e) {
      console.error(e);
    }
  }

  async startSession() {
    const title = prompt("Enter Session Title:", "Machine Learning & AI Interactive Session");
    if (!title) return;
    try {
      await fetch('/api/session/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: title, instructor: "Prof. Sarah Jenkins" })
      });
      window.location.reload();
    } catch (e) {
      console.error(e);
    }
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.appController = new AppController();
});
