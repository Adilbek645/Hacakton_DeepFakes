chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "analyzeBatch") {
<<<<<<< HEAD
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
=======
        console.log("Received analyzeBatch request for", request.texts?.length, "texts");
        
        // Wrap everything in an async IIFE to use await, but return true synchronously
        (async () => {
            try {
                const response = await fetch('http://localhost:5000/api/analyze_batch', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ texts: request.texts || [] })
                });

                if (!response.ok) {
                    let errorText = `Network response was not ok (${response.status})`;
                    try {
                        errorText = await response.text() || errorText;
                    } catch (e) {
                        // Ignore text parsing errors
                    }
                    console.error('Bad response from server:', response.status, errorText);
                    sendResponse({ success: false, error: errorText, status: response.status });
                    return;
                }

                const data = await response.json();
                sendResponse({ success: true, data: data });
            } catch (error) {
                console.error('Error in background fetch:', error);
                sendResponse({ success: false, error: error ? error.toString() : "Unknown error" });
>>>>>>> be15044a33d676e9c6da0ece6eed380ddb36a0f5
            }
        })();
        
        // Return true to indicate we will send response asynchronously
        return true; 
    }
});
