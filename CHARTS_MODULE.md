# MedPulse Charts Module

## Overview
The MedPulse Charts Module adds meaningful, printable health visualizations to medical reports. All charts are generated using vanilla JavaScript Canvas API—no dependencies needed.

## Features

### 📊 Health Metrics Overview (Radar Chart)
- **Purpose**: Visualizes 6 key health dimensions
- **Metrics**: Cardiovascular, Nutrition, Mental Health, Physical Activity, Sleep Quality, Stress Level
- **Color**: Gradient fill showing overall health profile
- **Use Case**: Quick assessment of health balance across domains

### 🥗 Nutrition Distribution (Pie Chart)
- **Purpose**: Shows recommended macronutrient breakdown
- **Breakdown**: Proteins (30%), Carbs (45%), Fats (20%), Fiber (5%)
- **Features**: Slice labels with percentages, color-coded legend
- **Use Case**: Diet planning and nutritional education

### ✅ Recommendation Adherence (Horizontal Bar Chart)
- **Purpose**: Tracks progress toward health goals
- **Metrics**: Daily Exercise, Hydration, Sleep Schedule, Medication, Nutrition
- **Color Coding**: Green (75%+), Orange (50-74%), Yellow (<50%)
- **Use Case**: Motivational tracking for fitness and lifestyle goals

### ⚠️ Symptom Severity Analysis (Bar Chart)
- **Purpose**: Quantifies symptom intensity on 0-10 scale
- **Color Coding**: Green (0-4), Orange (5-7), Red (8-10)
- **Features**: Gridlines, axis labels, sorted by severity
- **Use Case**: Identifying primary health concerns

### 🎯 Health Journey Milestones (Timeline Chart)
- **Purpose**: Shows progress toward long-term health goals
- **Milestones**: Day 1, Week 1, Month 1, Quarter 1, Year 1
- **Status**: Completed (green), In-progress (amber), Pending (gray)
- **Use Case**: Long-term health goal tracking and motivation

## Integration

### Adding Charts to Reports
```javascript
// Render all charts in a container
MedChartsEngine.renderCharts(container, reportData);

// Or render individual charts
MedChartsEngine.createHealthRadarChart(container, metricsObject);
MedChartsEngine.createNutritionPieChart(container, nutritionObject);
MedChartsEngine.createAdherenceBarChart(container, adherenceObject);
MedChartsEngine.createSeverityChart(container, symptomObject);
MedChartsEngine.createMilestoneTimelineChart(container, milestonesArray);
```

### Data Extraction
The module automatically extracts health insights from report text:
```javascript
const metrics = MedChartsEngine.extractMetricsFromContent(reportText);
```

## Styling

### CSS Variables Used
- `--primary`: Main accent color (#2d5016)
- `--secondary`: Secondary color (#4a7c28)
- `--accent`: Chart highlight (#7db84e)
- `--danger`: High severity (#8b2020)
- `--warning`: Medium severity (#7a4f00)

### Print Support
All charts are CSS media query optimized for PDF printing:
- Canvas elements scale responsively
- No page breaks within charts
- High-quality rendering at print resolution

## Browser Compatibility
- Chrome 87+
- Firefox 78+
- Safari 14+
- Edge 87+
- Mobile browsers (iOS Safari, Chrome Mobile)

## File Size
- `charts.js`: ~12KB (minified: ~5KB)
- No external dependencies
- Canvas-based rendering (lightweight)

## Performance
- Instant render (<100ms per chart)
- Memory efficient (single canvas per chart)
- No layout thrashing
- Smooth 60fps animations optional

## Future Enhancements
- Interactive tooltips on hover
- Animation on chart load
- Data export to CSV/JSON
- Customizable color palettes
- Real-time data updates
- Dark mode support
