// Graphique en ligne (Inpatients vs Outpatients Trend)
const ctxTrend = document.getElementById('trendChart').getContext('2d');
const trendChart = new Chart(ctxTrend, {
    type: 'line',
    data: {
        labels: dashboardData.trend_labels,
        datasets: [
            {
                label: 'Inpatients',
                data: dashboardData.trend_in_data,
                borderColor: '#6c5ce7',
                backgroundColor: 'rgba(108,92,231,.12)',
                fill: true,
                tension: .45,
                pointRadius: 0,
                pointHoverRadius: 5,
                borderWidth: 2.5
            },
            {
                label: 'Outpatients',
                data: dashboardData.trend_out_data,
                borderColor: '#00d2d3',
                backgroundColor: 'rgba(0,210,211,.08)',
                fill: true,
                tension: .45,
                pointRadius: 0,
                pointHoverRadius: 5,
                borderWidth: 2
            }
        ]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 1000, easing: 'easeInOutQuad' },
        plugins: { legend: { display: true, position: 'top', labels: { boxWidth: 10, padding: 15 } }, tooltip: { mode: 'index', intersect: false } },
        scales: {
            x: { grid: { display: false }, ticks: { maxRotation: 0 } },
            y: { grid: { display: false }, beginAtZero: false }
        },
        interaction: { mode: 'nearest', axis: 'x', intersect: false }
    }
});

// Graphique Donut (Gender)
const ctxGender = document.getElementById('genderChart').getContext('2d');
const genderChart = new Chart(ctxGender, {
    type: 'doughnut',
    data: {
        labels: ['Female', 'Male'],
        datasets: [{
            data: dashboardData.gender_data,
            backgroundColor: ['#0d9488','#38bdf8'],
            borderColor: '#f8fafc',
            borderWidth: 3,
            hoverOffset: 8
        }]
    },
    options: {
        responsive: true, maintainAspectRatio: false, cutout: '70%',
        animation: { duration: 1000, easing: 'easeInOutQuad' },
        plugins: {
            legend: { display: false },
            tooltip: { callbacks: { label: c => ` ${c.label}: ${c.parsed}%` } }
        }
    }
});

// Graphique à barres (Department)
const ctxDepartment = document.getElementById('departmentChart').getContext('2d');
const departmentChart = new Chart(ctxDepartment, {
    type: 'bar',
    data: {
        labels: dashboardData.dept_labels,
        datasets: [{
            data: dashboardData.dept_data,
            backgroundColor: ['#6c5ce7', '#00d2d3', '#ff7675', '#ffa726', '#ab47bc'],
            borderRadius: 5,
            barThickness: 20
        }]
    },
    options: {
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 1000, easing: 'easeInOutQuad' },
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true }, x: { grid: { display: false } } }
    }
});

// Graphique Pie (Staff by Role)
const ctxStaff = document.getElementById('staffChart').getContext('2d');
const staffChart = new Chart(ctxStaff, {
    type: 'pie',
    data: {
        labels: dashboardData.staff_labels,
        datasets: [{
            data: dashboardData.staff_data,
            backgroundColor: ['#6c5ce7', '#00d2d3', '#ff7675'],
            borderWidth: 2,
            borderColor: '#fff'
        }]
    },
    options: {
        responsive: true, maintainAspectRatio: false,
        animation: { duration: 1000, easing: 'easeInOutQuad' },
        plugins: { legend: { position: 'bottom' } }
    }
});

// Graphique Pie (Vehicles Available vs In Mission)
const ctxVehicles = document.getElementById('vehiclesChart').getContext('2d');
const vehiclesChart = new Chart(ctxVehicles, {
    type: 'bar',
    data: {
        labels: ['Available','In Mission','Maintenance'],
        datasets: [{
            data: dashboardData.vehicles_data,
            backgroundColor: ['rgba(52,211,153,.7)','rgba(251,146,60,.7)','rgba(248,113,113,.7)'],
            borderRadius: 5,
            barThickness: 28
        }]
    },
    options: {
        responsive: true, maintainAspectRatio: false, indexAxis: 'y',
        animation: { duration: 1000, easing: 'easeInOutQuad' },
        plugins: { legend: { display: false } },
        scales: {
            x: { grid: { display: false }, beginAtZero: true, ticks: { stepSize: 5 } },
            y: { grid: { display: false } }
        }
    }
});

// Function to update department table
function updateDeptTable(data, labels, statuses) {
    const depts = [];
    for (let i = 0; i < labels.length; i++) {
        let badge = 'badge-blue';
        let label = '→ Stable';
        if (statuses[i] === 'Increasing') {
            badge = 'badge-green';
            label = '↑ Increasing';
        } else if (statuses[i] === 'Decreasing') {
            badge = 'badge-red';
            label = '↓ Decreasing';
        }
        depts.push({ name: labels[i], count: data[i], badge: badge, label: label });
    }
    const max = Math.max(...depts.map(d => d.count));
    const tbody = document.getElementById('deptBody');
    tbody.innerHTML = '';
    depts.forEach(d => {
        tbody.innerHTML += `
            <tr>
                <td>
                    ${d.name}
                    <div class="bar-track" style="width:90px;"><div class="bar-fill" style="width:${d.count/max*100}%"></div></div>
                </td>
                <td style="font-weight:700">${d.count}</td>
                <td><span class="dept-badge ${d.badge}">${d.label}</span></td>
            </tr>`;
    });
}

// Initial update for dept table
updateDeptTable(dashboardData.dept_data, dashboardData.dept_labels, dashboardData.dept_status);

// Connect to SocketIO for real-time updates
const socket = io();

socket.on('update_data', function(data) {
    // Update trend
    trendChart.data.labels = data.trend_labels;
    trendChart.data.datasets[0].data = data.trend_in_data;
    trendChart.data.datasets[1].data = data.trend_out_data;
    trendChart.update();

    // Update department
    departmentChart.data.datasets[0].data = data.dept_data;
    departmentChart.update();

    // Update gender
    genderChart.data.datasets[0].data = data.gender_data;
    genderChart.update();

    // Update staff
    staffChart.data.datasets[0].data = data.staff_data;
    staffChart.update();

    // Update vehicles
    vehiclesChart.data.datasets[0].data = data.vehicles_data;
    vehiclesChart.update();

    // Update dept table
    updateDeptTable(data.dept_data, data.dept_labels, data.dept_status);
});