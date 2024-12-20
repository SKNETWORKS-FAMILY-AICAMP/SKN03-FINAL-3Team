document.addEventListener('DOMContentLoaded', function() {
    var calendarEl = document.getElementById('calendar');
    let popup = document.querySelector('dialog');
    
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        googleCalendarApiKey: "{{ google_calendar_api_key }}", // API 키 삽입
        events: {
            googleCalendarId: "{{ google_calendar_id }}" // 캘린더 ID 삽입
        },
        eventClick: function(info) {
            info.jsEvent.preventDefault();

            popup.querySelector('div').innerHTML = `
            <h3>${info.event.title}</h3>
            <div>${info.event.extendedProps.description}</div>
            `;
            popup.setAttribute('open', 'open');
        }
    });
    calendar.render();
    popup.querySelector('button').addEventListener('click', ()=>{
        popup.removeAttribute('open');
    });
});

  





 
