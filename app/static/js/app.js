document.addEventListener('DOMContentLoaded', function() {
    const ctx = document.getElementById('seasonalSalesChart').getContext('2d');
    const salesData = {{ sales_data | tojson }};

    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: salesData.dates,
            datasets: [{
                label: 'Total Sales',
                data: salesData.amounts,
                borderColor: 'rgba(75, 192, 192, 1)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                fill: true,
            }]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    }
                },
                y: {
                    beginAtZero: true
                }
            }
        }
    });
});
