// function to update the alarm level and pit depth to /update_settings
function updateSettings() {
  // Get the alarm level and pit depth from the input elements
  var alarmLevel = document.getElementById('alarmLevel').value;
  var pitDepth = document.getElementById('pitDepth').value;
  var sumpId = document.getElementById('sumpId').value;
  
  // Construct a FormData object to send the data as form data with application/x-www-form-urlencoded encoding
  const formData = new FormData();
  formData.append('sump_id', sumpId);
  formData.append('alarm_level', alarmLevel);
  formData.append('pit_depth', pitDepth);

  // Send a POST request to /update_settings as form data with application/x-www-form-urlencoded encoding
  fetch('/settings', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams(formData),
  })
    // Update the plot after the POST request is complete
    .then(response => updatePlot())
    .catch(error => console.error('Error updating settings:', error));
}

// Function to pad zero to single-digit numbers
function padZero(num) {
  return num < 10 ? '0' + num : num;
}

// Function to request a rest from /reset endpoint
function clearLocalStorage() {
  fetch('/reset')
    .then(response => updatePlot())
    .catch(error => console.error('Error resetting:', error));
}

function updatePlot() {
  // Fetch sump_id, pit_depth, alarm_level from /settings endpoint  
  // Fetch streaming data from /data endpoint with the format [[timestamp, distance], ...]
  const settings_request = fetch('/settings').then(response => response.json());
  const data_request = fetch('/data').then(response => response.text());

  Promise.all([settings_request, data_request])
  .then(([settingsJSON, dataString]) => {
    // Extract fields from the fetched settings data
    var pitDepth = settingsJSON.pit_depth || 999;
    var alarmLevel = settingsJSON.alarm_level || 0;
    var sumpId = settingsJSON.sump_id || "Unknown";

    // Add sumpid, pit depth, and alarm level to the HTML elements
    document.getElementById('sumpId').value = sumpId;
    document.getElementById('pitDepth').value = pitDepth;
    document.getElementById('alarmLevel').value = alarmLevel;

    // Define regular expression patterns for extracting timestamps and distances
    const timestampPattern = /\[(.*?)\s-\d+:\d+\s*,\s*([0-9.]+)\]/g;

    // Arrays to store timestamps and distances
    const timestamps = [];
    const distances = [];

    // Extract matches using the regular expression
    let match;
    while ((match = timestampPattern.exec(dataString)) !== null) {
      timestamps.push(match[1]);
      distances.push(parseFloat(match[2]));
    }
    
    // Calculate the max and min distances
    var maxDistance = Math.max(...distances);
    var minDistance = Math.min(...distances);

    document.getElementById('maxDistance').innerHTML = maxDistance || 0;
    document.getElementById('minDistance').innerHTML = minDistance || 0;

    // Convert timestamps from string to Date objects
    // timestamps = timestamps.map(timestamp => new Date(timestamp));

    // Water level is the pit depth minus the distance
    var waterLevels = distances.map(distance => pitDepth - distance);

    console.log(waterLevels);

    // Create the time series mountain plot
    var trace = {
      x: timestamps,
      y: waterLevels,
      type: 'scatter',
      mode: 'lines',
      fill: 'tozeroy',
      line: {
        color: 'rgb(0, 100, 255)',
      },
      name: 'Sump Water Levels',
    };


    var layout = {
      xaxis: {
        title: {
          // text: 'Timestamp',
          font: {
            color: 'white',  // X-axis title text color
          },
        },
        tickfont: {
          color: 'white',  // Tick label text color
        },
        tickformat: '%I:%M %p', // Format as HH:MM in 12-hour format
        showgrid: true,  // Display grid lines on the x-axis
        gridcolor: 'gray',  // Set grid lines color
      },
      yaxis: {
        title: {
          text: 'Distance to water (cm)',
          font: {
            color: 'white',  // Y-axis title text color
          },
        },
        tickfont: {
          color: 'white',  // Y-axis tick label text color
        },
        showgrid: true,  // Display grid lines on the y-axis
        gridcolor: 'gray',  // Set grid lines color
      },
      legend: {
        font: {
          color: 'white',  // Legend font color
        },
        // x: 0,   // Set x to 0 for left alignment
        // y: 1.2, // Set y to -0.2 for below the chart
      },
      paper_bgcolor: 'rgba(0,0,0,0.1)',  // Transparent background color of the chart
      plot_bgcolor: 'rgba(0,0,0,0)',     // Transparent background color of the plot area
      shapes: [
      // Create a trace for the alarmLevel horizontal line
      {
        type: 'line',
        x0: timestamps[0],
        x1: timestamps[timestamps.length - 1],
        y0: alarmLevel,
        y1: alarmLevel,
        line: {
            color: 'red',
            width: 2,
            dash: 'dash',
        },
        name: 'Alarm Level',
      },
      // Create a trace for the pitDepth horizontal line
      {
        type: 'line',
        x0: timestamps[0],
        x1: timestamps[timestamps.length - 1],
        y0: pitDepth,
        y1: pitDepth,
        line: {
            color: 'green',
            width: 2,
            dash: 'dash',
        },
        name: 'Pit Depth',
      }
    ]
    };

    // Combine traces and layout, and create the plot      
    const plotData = [trace]//, alarmLevelLine, pitDepthLine];

    // Use Plotly to create or update the plot
    Plotly.newPlot('time-series-plot', plotData, layout);

    // User input for alarm level and pit depth
    var alarmLevelInput = document.getElementById('alarmLevel');
    var alarmLevel = parseFloat(alarmLevelInput.value);

    var pitDepthInput = document.getElementById('pitDepth');
    var pitDepth = parseFloat(pitDepthInput.value);

    var sumpIdInput = document.getElementById('sumpId');
    var sumpId = sumpIdInput.value;

  })
  .catch(error => console.error('Error fetching data:', error));
}

// Call the updatePlot function initially
updatePlot();

// Set up an interval to update the plot every 5 mins
setInterval(updatePlot, 5 * 3600 * 1000);