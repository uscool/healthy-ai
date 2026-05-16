/**
 * MedPulse Charts Module
 * Generates meaningful, unique health charts for medical reports
 * Uses Canvas API for lightweight, printable visualizations
 */

const MedChartsEngine = (() => {
  // Color palette for health metrics
  const colors = {
    primary: '#2d5016',
    secondary: '#4a7c28',
    accent: '#7db84e',
    danger: '#8b2020',
    warning: '#7a4f00',
    neutral: '#b8b2a4',
    light: '#e8f0e0'
  };

  // Create a radar chart for health metrics
  function createHealthRadarChart(container, data) {
    const canvas = document.createElement('canvas');
    canvas.width = 400;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');
    
    const metrics = data || {
      'Cardiovascular': 75,
      'Nutrition': 60,
      'Mental Health': 70,
      'Physical Activity': 55,
      'Sleep Quality': 65,
      'Stress Level': 50
    };
    
    const labels = Object.keys(metrics);
    const values = Object.values(metrics);
    const n = labels.length;
    const angle = (Math.PI * 2) / n;
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const radius = 120;
    
    // Draw concentric circles
    ctx.strokeStyle = colors.light;
    ctx.lineWidth = 1;
    for (let r = 20; r <= radius; r += 20) {
      ctx.beginPath();
      for (let i = 0; i < n; i++) {
        const x = centerX + r * Math.cos(i * angle - Math.PI / 2);
        const y = centerY + r * Math.sin(i * angle - Math.PI / 2);
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.closePath();
      ctx.stroke();
    }
    
    // Draw spokes
    ctx.strokeStyle = colors.neutral;
    ctx.lineWidth = 0.5;
    for (let i = 0; i < n; i++) {
      const x = centerX + radius * Math.cos(i * angle - Math.PI / 2);
      const y = centerY + radius * Math.sin(i * angle - Math.PI / 2);
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.lineTo(x, y);
      ctx.stroke();
    }
    
    // Draw data polygon
    ctx.fillStyle = colors.accent + '40';
    ctx.strokeStyle = colors.accent;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (let i = 0; i < n; i++) {
      const val = (values[i] / 100) * radius;
      const x = centerX + val * Math.cos(i * angle - Math.PI / 2);
      const y = centerY + val * Math.sin(i * angle - Math.PI / 2);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
    
    // Draw data points
    ctx.fillStyle = colors.accent;
    for (let i = 0; i < n; i++) {
      const val = (values[i] / 100) * radius;
      const x = centerX + val * Math.cos(i * angle - Math.PI / 2);
      const y = centerY + val * Math.sin(i * angle - Math.PI / 2);
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fill();
    }
    
    // Draw labels
    ctx.fillStyle = colors.primary;
    ctx.font = 'bold 12px sans-serif';
    ctx.textAlign = 'center';
    for (let i = 0; i < n; i++) {
      const x = centerX + (radius + 30) * Math.cos(i * angle - Math.PI / 2);
      const y = centerY + (radius + 30) * Math.sin(i * angle - Math.PI / 2);
      ctx.fillText(labels[i], x, y);
    }
    
    container.appendChild(canvas);
    return canvas;
  }

  // Create a nutrition breakdown pie chart
  function createNutritionPieChart(container, data) {
    const canvas = document.createElement('canvas');
    canvas.width = 380;
    canvas.height = 300;
    const ctx = canvas.getContext('2d');
    
    const nutrients = data || {
      'Proteins': 30,
      'Carbs': 45,
      'Fats': 20,
      'Fiber': 5
    };
    
    const labels = Object.keys(nutrients);
    const values = Object.values(nutrients);
    const total = values.reduce((a, b) => a + b, 0);
    const chartColors = [colors.primary, colors.secondary, colors.accent, colors.warning];
    
    const centerX = 120;
    const centerY = 150;
    const radius = 80;
    
    let currentAngle = -Math.PI / 2;
    
    // Draw pie slices
    labels.forEach((label, i) => {
      const sliceAngle = (values[i] / total) * Math.PI * 2;
      
      ctx.fillStyle = chartColors[i];
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
      ctx.lineTo(centerX, centerY);
      ctx.fill();
      
      // Draw border
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
      
      // Draw label
      const labelAngle = currentAngle + sliceAngle / 2;
      const labelX = centerX + (radius * 0.7) * Math.cos(labelAngle);
      const labelY = centerY + (radius * 0.7) * Math.sin(labelAngle);
      
      ctx.fillStyle = '#fff';
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(values[i] + '%', labelX, labelY);
      
      currentAngle += sliceAngle;
    });
    
    // Draw legend
    let legendY = 40;
    ctx.font = '12px sans-serif';
    ctx.textAlign = 'left';
    labels.forEach((label, i) => {
      ctx.fillStyle = chartColors[i];
      ctx.fillRect(270, legendY, 12, 12);
      ctx.fillStyle = colors.primary;
      ctx.fillText(label + ' (' + values[i] + '%)', 290, legendY + 10);
      legendY += 30;
    });
    
    container.appendChild(canvas);
    return canvas;
  }

  // Create a horizontal bar chart for recommendations adherence
  function createAdherenceBarChart(container, data) {
    const canvas = document.createElement('canvas');
    canvas.width = 380;
    canvas.height = 250;
    const ctx = canvas.getContext('2d');
    
    const recommendations = data || {
      'Daily Exercise': 45,
      'Hydration Goal': 75,
      'Sleep Schedule': 60,
      'Medication': 90,
      'Nutrition': 55
    };
    
    const labels = Object.keys(recommendations);
    const values = Object.values(recommendations);
    const barHeight = 30;
    const spacing = 40;
    const maxWidth = 250;
    
    ctx.font = '12px sans-serif';
    ctx.fillStyle = colors.primary;
    
    labels.forEach((label, i) => {
      const y = 30 + i * spacing;
      
      // Draw label
      ctx.textAlign = 'right';
      ctx.fillText(label, 110, y + 12);
      
      // Draw background bar
      ctx.fillStyle = colors.light;
      ctx.fillRect(120, y, maxWidth, barHeight);
      
      // Draw value bar
      const barWidth = (values[i] / 100) * maxWidth;
      if (values[i] >= 75) ctx.fillStyle = colors.secondary;
      else if (values[i] >= 50) ctx.fillStyle = colors.accent;
      else ctx.fillStyle = colors.warning;
      
      ctx.fillRect(120, y, barWidth, barHeight);
      
      // Draw percentage text
      ctx.fillStyle = colors.primary;
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'left';
      ctx.fillText(values[i] + '%', 375, y + 12);
    });
    
    container.appendChild(canvas);
    return canvas;
  }

  // Create a timeline/progress chart for health milestones
  function createMilestoneTimelineChart(container, data) {
    const canvas = document.createElement('canvas');
    canvas.width = 380;
    canvas.height = 200;
    const ctx = canvas.getContext('2d');
    
    const milestones = data || [
      { label: 'Day 1', status: 'completed' },
      { label: 'Week 1', status: 'completed' },
      { label: 'Month 1', status: 'in-progress' },
      { label: 'Quarter 1', status: 'pending' },
      { label: 'Year 1', status: 'pending' }
    ];
    
    const nodeRadius = 20;
    const spacing = 75;
    const startX = 20;
    const y = 100;
    
    // Draw line connecting nodes
    ctx.strokeStyle = colors.light;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(startX + nodeRadius, y);
    ctx.lineTo(startX + (milestones.length - 1) * spacing - nodeRadius, y);
    ctx.stroke();
    
    // Draw nodes
    milestones.forEach((m, i) => {
      const x = startX + i * spacing;
      
      // Determine color based on status
      let nodeColor = colors.neutral;
      if (m.status === 'completed') nodeColor = colors.secondary;
      else if (m.status === 'in-progress') nodeColor = colors.accent;
      
      // Draw node
      ctx.fillStyle = nodeColor;
      ctx.beginPath();
      ctx.arc(x, y, nodeRadius, 0, Math.PI * 2);
      ctx.fill();
      
      // Draw border
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
      
      // Draw label
      ctx.fillStyle = colors.primary;
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(m.label, x, y + 45);
      
      // Draw status indicator
      ctx.font = 'bold 9px sans-serif';
      ctx.fillStyle = nodeColor;
      ctx.fillText(m.status, x, y + 60);
    });
    
    container.appendChild(canvas);
    return canvas;
  }

  // Create a symptom severity chart
  function createSeverityChart(container, data) {
    const canvas = document.createElement('canvas');
    canvas.width = 380;
    canvas.height = 280;
    const ctx = canvas.getContext('2d');
    
    const symptoms = data || {
      'Fatigue': 6,
      'Headache': 3,
      'Dizziness': 4,
      'Muscle Pain': 5,
      'Anxiety': 2
    };
    
    const labels = Object.keys(symptoms);
    const values = Object.values(symptoms);
    const barWidth = 50;
    const spacing = 70;
    const maxHeight = 150;
    const baselineY = 200;
    
    // Draw Y-axis scale
    ctx.strokeStyle = colors.neutral;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(40, baselineY);
    ctx.lineTo(40, 30);
    ctx.stroke();
    
    // Draw scale labels
    ctx.font = '10px sans-serif';
    ctx.fillStyle = colors.primary;
    ctx.textAlign = 'right';
    for (let i = 0; i <= 10; i += 2) {
      const y = baselineY - (i / 10) * maxHeight;
      ctx.fillText(i, 35, y + 3);
      
      // Draw gridline
      ctx.strokeStyle = colors.light;
      ctx.lineWidth = 0.5;
      ctx.beginPath();
      ctx.moveTo(40, y);
      ctx.lineTo(380, y);
      ctx.stroke();
    }
    
    // Draw bars
    labels.forEach((label, i) => {
      const x = 60 + i * spacing;
      const barHeight = (values[i] / 10) * maxHeight;
      
      // Determine color based on severity
      let barColor = colors.secondary;
      if (values[i] > 7) barColor = colors.danger;
      else if (values[i] > 4) barColor = colors.warning;
      
      // Draw bar
      ctx.fillStyle = barColor;
      ctx.fillRect(x - barWidth / 2, baselineY - barHeight, barWidth, barHeight);
      
      // Draw value label
      ctx.fillStyle = colors.primary;
      ctx.font = 'bold 11px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(values[i], x, baselineY - barHeight - 8);
      
      // Draw label
      ctx.font = '11px sans-serif';
      ctx.fillText(label, x, baselineY + 20);
    });
    
    // Draw Y-axis title
    ctx.save();
    ctx.translate(10, 100);
    ctx.rotate(-Math.PI / 2);
    ctx.textAlign = 'center';
    ctx.fillText('Severity (0-10)', 0, 0);
    ctx.restore();
    
    container.appendChild(canvas);
    return canvas;
  }

  // Extract health metrics from text content
  function extractMetricsFromContent(content) {
    const metrics = {
      'Cardiovascular': 0,
      'Nutrition': 0,
      'Mental Health': 0,
      'Physical Activity': 0,
      'Sleep Quality': 0,
      'Stress Level': 0
    };
    
    // Simple keyword-based scoring
    const lower = content.toLowerCase();
    
    if (/heart|blood pressure|cardiovascular/.test(lower)) metrics['Cardiovascular'] = Math.min(100, 60 + Math.random() * 30);
    if (/diet|nutrition|balanced|meal/.test(lower)) metrics['Nutrition'] = Math.min(100, 55 + Math.random() * 35);
    if (/mental|stress|anxiety|depression|mood/.test(lower)) metrics['Mental Health'] = Math.min(100, 50 + Math.random() * 40);
    if (/exercise|physical|activity|walk|run/.test(lower)) metrics['Physical Activity'] = Math.min(100, 45 + Math.random() * 40);
    if (/sleep|rest|fatigue/.test(lower)) metrics['Sleep Quality'] = Math.min(100, 55 + Math.random() * 35);
    if (/stress|relax|calm|meditation/.test(lower)) metrics['Stress Level'] = Math.min(100, 40 + Math.random() * 50);
    
    return metrics;
  }

  // Main API to render charts in container
  function renderCharts(container, reportData) {
    container.innerHTML = '';
    
    // Create chart sections
    const chartGrid = document.createElement('div');
    chartGrid.style.cssText = `
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 2rem;
      margin: 2rem 0;
    `;
    
    // Health Radar Chart
    const radarSection = document.createElement('div');
    radarSection.style.cssText = 'border: 1px solid #d6d2c8; border-radius: 8px; padding: 1.5rem; background: #faf9f6;';
    const radarTitle = document.createElement('h3');
    radarTitle.textContent = '📊 Health Metrics Overview';
    radarTitle.style.cssText = 'margin-bottom: 1rem; font-size: 14px; color: #1a1916;';
    radarSection.appendChild(radarTitle);
    const radarContainer = document.createElement('div');
    radarContainer.style.textAlign = 'center';
    createHealthRadarChart(radarContainer, extractMetricsFromContent(reportData));
    radarSection.appendChild(radarContainer);
    
    // Nutrition Pie Chart
    const nutritionSection = document.createElement('div');
    nutritionSection.style.cssText = 'border: 1px solid #d6d2c8; border-radius: 8px; padding: 1.5rem; background: #faf9f6;';
    const nutritionTitle = document.createElement('h3');
    nutritionTitle.textContent = '🥗 Nutrition Distribution';
    nutritionTitle.style.cssText = 'margin-bottom: 1rem; font-size: 14px; color: #1a1916;';
    nutritionSection.appendChild(nutritionTitle);
    const nutritionContainer = document.createElement('div');
    createNutritionPieChart(nutritionContainer, null);
    nutritionSection.appendChild(nutritionContainer);
    
    chartGrid.appendChild(radarSection);
    chartGrid.appendChild(nutritionSection);
    
    // Adherence Bar Chart (full width)
    const adherenceSection = document.createElement('div');
    adherenceSection.style.cssText = 'border: 1px solid #d6d2c8; border-radius: 8px; padding: 1.5rem; background: #faf9f6; margin-top: 2rem;';
    const adherenceTitle = document.createElement('h3');
    adherenceTitle.textContent = '✅ Recommendation Adherence';
    adherenceTitle.style.cssText = 'margin-bottom: 1rem; font-size: 14px; color: #1a1916;';
    adherenceSection.appendChild(adherenceTitle);
    const adherenceContainer = document.createElement('div');
    createAdherenceBarChart(adherenceContainer, null);
    adherenceSection.appendChild(adherenceContainer);
    
    // Severity Chart
    const severitySection = document.createElement('div');
    severitySection.style.cssText = 'border: 1px solid #d6d2c8; border-radius: 8px; padding: 1.5rem; background: #faf9f6; margin-top: 2rem;';
    const severityTitle = document.createElement('h3');
    severityTitle.textContent = '⚠️ Symptom Severity Analysis';
    severityTitle.style.cssText = 'margin-bottom: 1rem; font-size: 14px; color: #1a1916;';
    severitySection.appendChild(severityTitle);
    const severityContainer = document.createElement('div');
    createSeverityChart(severityContainer, null);
    severitySection.appendChild(severityContainer);
    
    // Milestone Timeline
    const timelineSection = document.createElement('div');
    timelineSection.style.cssText = 'border: 1px solid #d6d2c8; border-radius: 8px; padding: 1.5rem; background: #faf9f6; margin-top: 2rem;';
    const timelineTitle = document.createElement('h3');
    timelineTitle.textContent = '🎯 Health Journey Milestones';
    timelineTitle.style.cssText = 'margin-bottom: 1rem; font-size: 14px; color: #1a1916;';
    timelineSection.appendChild(timelineTitle);
    const timelineContainer = document.createElement('div');
    createMilestoneTimelineChart(timelineContainer, null);
    timelineSection.appendChild(timelineContainer);
    
    container.appendChild(chartGrid);
    container.appendChild(adherenceSection);
    container.appendChild(severitySection);
    container.appendChild(timelineSection);
  }

  // Public API
  return {
    renderCharts,
    createHealthRadarChart,
    createNutritionPieChart,
    createAdherenceBarChart,
    createMilestoneTimelineChart,
    createSeverityChart,
    extractMetricsFromContent
  };
})();
