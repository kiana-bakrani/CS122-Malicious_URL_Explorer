// Chart controls are applied only when the user submits the Results form.
const chartChoices = document.querySelectorAll('input[name="view"]');
const timeSeriesControls = document.getElementById('timeseries-group-controls');

function updateChartControls() {
    const selected = document.querySelector('input[name="view"]:checked');
    if (timeSeriesControls && selected) {
        timeSeriesControls.hidden = selected.value === 'map';
    }
}

chartChoices.forEach(choice => choice.addEventListener('change', updateChartControls));
updateChartControls();
