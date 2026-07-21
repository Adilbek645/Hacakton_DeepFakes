chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "analyzeBatch") {
        fetch('http://127.0.0.1:5000/api/analyze_batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ texts: request.texts })
        })
        .then(async response => {
            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`Server Error (${response.status}): ${errText}`);
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
