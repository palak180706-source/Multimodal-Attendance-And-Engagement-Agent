/**
 * EngagementChartsController:
 * Real-time Chart.js streaming for Multimodal Engagement Curves
 */
class EngagementChartsController {
  constructor() {
    this.chart = null;
    this.maxPoints = 25;
    this.initChart();
  }

  initChart() {
    const ctx = document.getElementById('engagementChart');
    if (!ctx) return;

    this.chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Fused Engagement E(t)',
            data: [],
            borderColor: '#6366f1',
            backgroundColor: 'rgba(99, 102, 241, 0.15)',
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointRadius: 3,
            pointBackgroundColor: '#6366f1'
          },
          {
            label: 'Visual Attention (V_attn)',
            data: [],
            borderColor: '#10b981',
            borderWidth: 2,
            borderDash: [5, 5],
            fill: false,
            tension: 0.3,
            pointRadius: 0
          },
          {
            label: 'Audio Interaction (A_int)',
            data: [],
            borderColor: '#0ea5e9',
            borderWidth: 2,
            borderDash: [3, 3],
            fill: false,
            tension: 0.3,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 300 },
        scales: {
          x: {
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { size: 10 } }
          },
          y: {
            min: 0,
            max: 100,
            grid: { color: 'rgba(255, 255, 255, 0.05)' },
            ticks: { color: '#94a3b8', font: { size: 10 } }
          }
        },
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#e2e8f0', font: { size: 11 }, boxWidth: 12 }
          },
          tooltip: {
            mode: 'index',
            intersect: false
          }
        }
      }
    });
  }

  addSnapshot(snapshot) {
    if (!this.chart) return;

    const label = `${snapshot.seconds_from_start}s`;
    const labels = this.chart.data.labels;
    const datasets = this.chart.data.datasets;

    labels.push(label);
    datasets[0].data.push(snapshot.fused_score);
    datasets[1].data.push(snapshot.visual_attention);
    datasets[2].data.push(snapshot.audio_interaction);

    if (labels.length > this.maxPoints) {
      labels.shift();
      datasets.forEach(ds => ds.data.shift());
    }

    this.chart.update('none');
  }
}

window.EngagementChartsController = EngagementChartsController;
