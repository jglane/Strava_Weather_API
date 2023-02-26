// App variables
const CLIENT_SECRET = "e21011ffaf6116bca9b7549863804cd192cef64a";
var REFRESH_TOKEN = "9b192429890cbe7a668e122661dbdf2e2142c04c";
const CLIENT_ID = "101418";
const USER_ID = "26981131";
const IP_ADDRESS = "100.64.2.200";
const API_KEY = "1a4a9038a72f56b8627cfd39cacb98b6";

// HTML Objects
const button_get_activity = document.getElementById('get_activity');

document.addEventListener("readystatechange", async (event) => {
    if (sessionStorage.getItem("ACCESS_TOKEN") == null || sessionStorage.getItem("ACCESS_TOKEN") == 'undefined') {
        code = document.URL.match(/(?<=code=)\w+/g);
        if (code) {
            code = code[0];
            const response = await fetch(`https://www.strava.com/api/v3/oauth/token`, {
                method: "POST",
                headers: {
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    client_id: CLIENT_ID,
                    client_secret: CLIENT_SECRET,
                    code: code,
                    grant_type: "authorization_code"
                })
            });
            data = await response.json();
            console.log(data)
            sessionStorage.setItem("ACCESS_TOKEN", data.access_token);
            REFRESH_TOKEN = data.refresh_token;
        } else {
            console.error('Authorization code needed')
        }
    }
});

avg = (list) => {
    return list.reduce((a, b) => a + b) / list.length;
}

button_get_activity.addEventListener("click", (event) => {
    fetch('https://www.strava.com/api/v3/athlete/activities?per_page=10', {
        headers: {
            Authorization: `Bearer ${sessionStorage.getItem("ACCESS_TOKEN")}`
        }
    }).then(response => response.json()).then(activity_data => {
        const activity = activity_data[9];
        const start_date = Date.parse(activity.start_date) / 1000;
        const end_date = start_date + activity.elapsed_time;
        console.log(activity.start_date, start_date)

        fetch(`https://history.openweathermap.org/data/2.5/history/city?lat=${activity.start_latlng[0]}&lon=${activity.start_latlng[1]}&start=${start_date}&end=${end_date}&units=imperial&appid=${API_KEY}`)
        .then(response => response.json()).then(weather_data => {
            console.log(weather_data)

            // Calculations
            const avg_temp = avg(weather_data.list.map(elem => elem.main.temp));
            const avg_wind_speed = avg(weather_data.list.map(elem => elem.wind.speed));
            const avg_wind_dir = avg(weather_data.list.map(elem => elem.wind.deg));
            var wind_arrow;
            if (-22.5 <= avg_wind_dir && avg_wind_dir < 22.5) { // N
                wind_arrow = String.fromCharCode(8595);
            } else if (22.5 <= avg_wind_dir && avg_wind_dir < 22.5 * 3) { // NE
                wind_arrow = String.fromCharCode(8601);
            } else if (22.5 * 3 <= avg_wind_dir && avg_wind_dir < 22.5 * 5) { // E
                wind_arrow = String.fromCharCode(8592);
            } else if (22.5 * 5 <= avg_wind_dir && avg_wind_dir < 22.5 * 7) { // SE
                wind_arrow = String.fromCharCode(8598);
            } else if (22.5 * 7 <= avg_wind_dir && avg_wind_dir < 22.5 * 9) { // S
                wind_arrow = String.fromCharCode(8593);
            } else if (22.5 * 9 <= avg_wind_dir && avg_wind_dir < 22.5 * 11) { // SW
                wind_arrow = String.fromCharCode(8599);
            } else if (22.5 * 11 <= avg_wind_dir && avg_wind_dir < 22.5 * 13) { // W
                wind_arrow = String.fromCharCode(8594);
            } else { // NW
                wind_arrow = String.fromCharCode(8600);
            }

            // Write description
            var description = `${Math.round(avg_temp)}${String.fromCharCode(176)}F | ${Math.round(avg_wind_speed * 10) / 10} mph ${wind_arrow}`;

            fetch(`https://www.strava.com/api/v3/activities/${activity.id}`, {
                method: 'PUT',
                headers: {
                    Authorization: `Bearer ${sessionStorage.getItem("ACCESS_TOKEN")}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    description: description
                })
            });
        });
    });
});