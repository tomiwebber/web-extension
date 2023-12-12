// Get the current tab's URL
chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
    var currentUrl = tabs[0].url;

    // Send the URL to your backend (Python)
    fetch('http://localhost:5000/analyze', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url: currentUrl }),
    })
    .then(response => response.json())
    .then(data => {
        // Display the analysis results in the extension popup
        document.getElementById('result').innerText = data.result; // Update the div with the result
        //document.getElementById('privacy_summary').textContent = data.privacy_summary;

        var listContainer = document.getElementById("privacy_summary");
        var fetchedPrivacySummary = data.privacy_summary;
        // Loop through each item in the list and create li elements to display them
        fetchedPrivacySummary.forEach(function(summary) {
            var listItem = document.createElement("p");
            listItem.textContent = summary;
            listContainer.appendChild(listItem);
        });
        
        var listContainer = document.getElementById("privacy_violations");
        var fetchedPrivacyViolations = data.privacy_violations;
        // Loop through each item in the list and create li elements to display them
        fetchedPrivacyViolations.forEach(function(violation) {
            var listItem = document.createElement("h4");
            listItem.textContent = violation;
            listContainer.appendChild(listItem);
        });

    })
    .catch(error => {
        console.error('Error:', error);
    });
});