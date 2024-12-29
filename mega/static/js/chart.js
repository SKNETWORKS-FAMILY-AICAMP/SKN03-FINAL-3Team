const ctx = document.getElementById('myChart').getContext('2d');
const myChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: {{ labels|safe }},
        datasets: [
            {
                label: 'TEAM04 + TEAM05 + TEAM06 질문 수',
                data: {{ team_questions|safe }},
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
            },
            {
                label: '기타 질문 수',
                data: {{ other_questions|safe }},
                backgroundColor: 'rgba(54, 162, 235, 0.2)',
            }
        ]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});