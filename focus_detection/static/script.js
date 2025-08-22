const video = document.getElementById('video');
const statusBox = document.getElementById('status');

navigator.mediaDevices.getUserMedia({ video: true })
.then(stream => {
    video.srcObject = stream;
    const track = stream.getVideoTracks()[0];
    const imageCapture = new ImageCapture(track);

    setInterval(() => {
        imageCapture.grabFrame().then(bitmap => {
            const canvas = document.createElement('canvas');
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(bitmap, 0, 0);

            canvas.toBlob(blob => {
                fetch('/analyze_frame', {
                    method: 'POST',
                    body: blob
                })
                .then(res => res.json())
                .then(data => {
                    if (data.status === "watching") {
                        statusBox.textContent = "Watching Screen 👁️";
                        statusBox.className = "watching";
                    } else if (data.status === "eyes_closed") {
                        statusBox.textContent = "Eyes Closed 😴";
                        statusBox.className = "eyes_closed";
                    } else {
                        statusBox.textContent = "Looking Away ❌";
                        statusBox.className = "away";
                    }
                });
            }, 'image/jpeg');
        });
    }, 500); // Update every 500ms
})
.catch(error => {
    console.error("Webcam error:", error);
});
