// Test script to verify SenseVoice download functionality
// This would typically be run in browser console

async function testSenseVoiceDownload() {
    try {
        // Test the downloadAdvancedModelStream function from backend-api.js
        const response = await fetch('api/download-sensevoice', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({})
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        console.log('Starting SenseVoice download test...');

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        console.log('Progress:', data);
                        
                        if (data.done) {
                            console.log('Download completed successfully!');
                            console.log('Model path:', data.path);
                            return data;
                        }
                    } catch (e) {
                        console.log('Raw data:', line);
                    }
                }
            }
        }
    } catch (error) {
        console.error('Download test failed:', error);
        throw error;
    }
}

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { testSenseVoiceDownload };
}
