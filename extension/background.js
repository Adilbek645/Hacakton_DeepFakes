chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "analyzeBatch") {
        fetch('http://localhost:5000/api/analyze_batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ texts: request.texts })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => sendResponse({ success: true, data: data }))
        .catch(error => {
            console.error('Error in background fetch:', error);
            sendResponse({ success: false, error: error.message });
        });
        
        // Return true to indicate we will send response asynchronously
        return true; 
    }
});
