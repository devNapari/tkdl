document.addEventListener("DOMContentLoaded", () => {
  const previewForm = document.getElementById("previewForm");
  const urlInput = document.getElementById("urlInput");
  const previewSection = document.getElementById("previewSection");
  const spinner = document.getElementById("previewSpinner");
  const videoPreview = document.getElementById("videoPreview");
  const videoThumbnail = document.getElementById("videoThumbnail");
  const downloadForm = document.getElementById("downloadForm");
  const downloadBtn = document.getElementById("downloadBtn");

  previewForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    spinner.classList.remove("hidden");
    previewSection.classList.remove("hidden");
    videoPreview.classList.add("hidden");
    videoThumbnail.classList.add("hidden");

    const formData = new FormData(previewForm);
    const response = await fetch("/preview", { method: "POST", body: formData });
    const data = await response.json();

    spinner.classList.add("hidden");

    if (data.error) {
      alert(data.error);
      return;
    }

    videoThumbnail.src = data.thumbnail;
    videoThumbnail.classList.remove("hidden");

    videoPreview.src = data.url;
    videoPreview.classList.remove("hidden");

    // Save URL for download
    downloadForm.dataset.url = urlInput.value;
  });

  downloadForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    downloadBtn.disabled = true;

    const formData = new FormData();
    formData.append("url", downloadForm.dataset.url);

    const response = await fetch("/download", { method: "POST", body: formData });
    if (!response.ok) {
      alert("Download failed");
      downloadBtn.disabled = false;
      return;
    }

    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = window.URL.createObjectURL(blob);
    link.download = "tiktok-video.mp4";
    link.click();

    downloadBtn.disabled = false;
  });
});
