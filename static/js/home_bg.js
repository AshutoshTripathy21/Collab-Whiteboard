function toggleTheme() {
    if (document.body.classList.contains("dark"))
        document.body.classList.remove("dark");
    else
        document.body.classList.add("dark");
}

document.addEventListener("DOMContentLoaded", function() {
    updateTimeAndDate();

    // Update time and date every second
    setInterval(updateTimeAndDate, 1000);
});

function updateTimeAndDate() {
    const timeAndDateElement = document.getElementById("timeAndDate");

    const now = new Date();

    // Format time as hh:mm am/pm
    const formattedTime = formatTime(now);

    // Format date as DDD • DD MMM
    const formattedDate = formatDate(now);

    // Combine time and date
    const timeAndDate = `${formattedTime}, ${formattedDate}`;

    timeAndDateElement.textContent = timeAndDate;
}

function formatTime(date) {
    let hours = date.getHours();
    let minutes = date.getMinutes();
    const ampm = hours >= 12 ? 'pm' : 'am';

    hours = hours % 12 || 12; // Convert to 12-hour format
    minutes = minutes < 10 ? '0' + minutes : minutes;

    return `${hours}:${minutes} ${ampm}`;
}

function formatDate(date) {
    const daysOfWeek = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    const dayOfWeek = daysOfWeek[date.getDay()];
    const dayOfMonth = date.getDate();
    const month = months[date.getMonth()];

    return `${dayOfWeek} • ${dayOfMonth} ${month}`;
}

